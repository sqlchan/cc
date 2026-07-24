import os
import sys
import json
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from http import HTTPStatus
from urllib import request
import dashscope
from dashscope.audio.asr import Transcription
from dashscope import Files
from dashscope import Generation

# 优先使用系统 ffmpeg，找不到时回退到 imageio-ffmpeg 内置版本
_system_ffmpeg = shutil.which('ffmpeg')
if _system_ffmpeg:
    FFMPEG = _system_ffmpeg
else:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ========== 配置 ==========
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
dashscope.api_key = 'sk-e7742091eeaa427880f0765456e6b2ae'


# 并发控制锁（保护 print 输出不交错）
_print_lock = threading.Lock()

# 并发数控制
MAX_WORKERS = 3


def safe_print(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)


def extract_audio(video_path, wav_path):
    """使用 ffmpeg 从视频中提取 16kHz 单声道 16bit WAV 音频"""
    safe_print(f'[1/4] 正在从视频提取音频: {os.path.basename(video_path)}')
    result = subprocess.run(
        [
            FFMPEG, '-y', '-i', video_path,
            '-vn',                # 去除视频流
            '-acodec', 'pcm_s16le',  # 16bit PCM 编码
            '-ar', '16000',       # 16kHz 采样率
            '-ac', '1',           # 单声道
            wav_path
        ],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg 错误: {result.stderr}')
    safe_print(f'音频提取完成: {os.path.basename(wav_path)}')


def upload_audio(wav_path):
    """上传音频文件到 DashScope 并获取下载 URL"""
    safe_print('[2/4] 正在上传音频到 DashScope...')
    upload_resp = Files.upload(
        file_path=wav_path,
        purpose='inference'
    )
    if upload_resp.status_code != HTTPStatus.OK:
        raise RuntimeError(f'上传失败: {upload_resp}')

    uploaded = upload_resp.output['uploaded_files'][0]
    file_id = uploaded['file_id']
    safe_print(f'上传成功, file_id: {file_id}')

    # 通过 file_id 获取下载 URL
    get_resp = Files.get(file_id=file_id)
    file_url = get_resp.output['url']
    return file_url


def transcribe_audio(file_url):
    """调用 DashScope ASR 转录音频"""
    safe_print('[3/4] 正在转录音频...')
    task_resp = Transcription.async_call(
        model='fun-asr',
        file_urls=[file_url],
        language_hints=['zh']
    )
    if task_resp.status_code != HTTPStatus.OK:
        raise RuntimeError(f'转录任务提交失败: {task_resp}')

    task_id = task_resp.output.task_id
    safe_print(f'任务已提交, task_id: {task_id}')
    safe_print('等待转录完成...')

    result_resp = Transcription.wait(task=task_id)
    if result_resp.status_code != HTTPStatus.OK:
        raise RuntimeError(f'转录失败: {result_resp}')

    # 解析转录结果
    texts = []
    for item in result_resp.output['results']:
        if item['subtask_status'] == 'SUCCEEDED':
            url = item['transcription_url']
            result_data = json.loads(request.urlopen(url).read().decode('utf8'))
            # 提取文本内容
            if 'transcripts' in result_data:
                for transcript in result_data['transcripts']:
                    if 'text' in transcript:
                        texts.append(transcript['text'])
            elif 'text' in result_data:
                texts.append(result_data['text'])
        else:
            safe_print(f'子任务失败: {item}')

    return '\n'.join(texts)


def polish_text(raw_text):
    """调用大模型对 ASR 原始文本进行轻度清理：分段、去口语词、修正识别错误"""
    safe_print('[4/4] 正在优化文本格式...')

    system_prompt = """你只需要对以下 ASR 转录文本做最轻度的处理：
1. 去掉口语化填充词（啊、哦、嗯、呢、吧、呃、哎、嘛、啦、呀等），只删除这些词，保留原文其他所有内容
2. 修正标点错误（如句号出现在句中，应改为逗号或删除）
3. 修正识别错误的词：paper→pip、cloud code→Claude Code、大鱼→大模型
4. 按语义自然分段，段落之间空一行

禁止事项：
- 不要改写原文，不要总结，不要重写，不要添加标题
- 不要删减原文内容
- 不要添加任何前言、总结、说明
- 直接输出处理后的文本即可"""

    resp = Generation.call(
        model='qwen-plus',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': raw_text}
        ],
        result_format='message'
    )

    if resp.status_code != HTTPStatus.OK:
        print(f'文本优化失败: {resp}, 将使用原始文本')
        return raw_text

    polished = resp.output.choices[0].message.content
    # 过滤掉 LLM 可能添加的前言和后缀
    polished = _strip_llm_wrapper(polished)
    print('文本优化完成')
    return polished


def _strip_llm_wrapper(text):
    """去除 LLM 输出的前言、分隔线、结束语等包装内容"""
    lines = text.split('\n')
    result = []
    in_content = False
    for line in lines:
        stripped = line.strip()
        # 跳过常见前言模式
        if not in_content:
            if stripped.startswith(('以下', '这是', '好的', '好的，', '好的,', '以下是', '这里是', '整理后的', '润色后的')):
                continue
            if stripped == '---':
                continue
            if not stripped:
                continue
            in_content = True
        # 跳过常见结束语
        if stripped.startswith(('如需', '欢迎', '如果', '如需我', '欢迎随时')):
            break
        if stripped == '---':
            break
        result.append(line)
    return '\n'.join(result).strip()


def save_text(text, video_path):
    """保存转录文本为 Markdown 文件"""
    md_path = os.path.splitext(video_path)[0] + '.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(text)
    safe_print(f'[5/5] 文本已保存: {os.path.basename(md_path)}')
    return md_path


SUPPORTED_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'}


def video_to_text(video_path):
    """主流程: 视频文件 → 提取音频 → ASR 转录 → 保存文本"""
    if not os.path.isfile(video_path):
        safe_print(f'错误: 文件不存在: {video_path}')
        return False

    # 将音频保存到视频同级目录
    wav_path = os.path.splitext(video_path)[0] + '.wav'

    try:
        extract_audio(video_path, wav_path)
        file_url = upload_audio(wav_path)
        text = transcribe_audio(file_url)
        polished = polish_text(text)
        save_text(polished, video_path)
        safe_print(f'[OK] {os.path.basename(video_path)} 转录完成!')
        return True
    except Exception as e:
        safe_print(f'[FAIL] {os.path.basename(video_path)} 处理失败: {e}')
        return False


def process_directory(dir_path):
    """并发处理目录下所有未转换过的视频"""
    if not os.path.isdir(dir_path):
        print(f'错误: 目录不存在: {dir_path}')
        sys.exit(1)

    video_files = []
    for fname in sorted(os.listdir(dir_path)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in SUPPORTED_EXTS:
            md_path = os.path.join(dir_path, os.path.splitext(fname)[0] + '.md')
            if not os.path.exists(md_path):
                video_files.append(os.path.join(dir_path, fname))

    if not video_files:
        print('没有未转换过的视频文件')
        return

    print(f'找到 {len(video_files)} 个待转换视频, 并发数: {MAX_WORKERS}\n')

    success = 0
    fail = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(video_to_text, vf): vf for vf in video_files}
        for future in as_completed(futures):
            vf = futures[future]
            if future.result():
                success += 1
            else:
                fail += 1

    print(f'\n全部处理完成! 成功: {success}, 失败: {fail}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python video.py <视频文件路径或目录>')
        print('示例: python video.py D:/videos/my_video.mp4')
        print('示例: python video.py D:/videos/')
        sys.exit(1)

    path = sys.argv[1]
    if os.path.isdir(path):
        process_directory(path)
    else:
        video_to_text(path)
