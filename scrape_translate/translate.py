"""翻译 Quickstart.md 为中文"""
import os
import json
import dashscope
from dashscope import Generation

dashscope.api_key = 'sk-e7742091eeaa427880f0765456e6b2ae'
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# Read scraped content via xcrawl
import subprocess
result = subprocess.run(
    [
        'curl', '-s', '-X', 'POST', 'https://run.xcrawl.com/v1/scrape',
        '-H', 'Authorization: Bearer xc-t5wyO5va9I5UMZKNFrD0vADZCM0z2rlwcpVtO6MnvaKxgFZg',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "url": "https://hermes-agent.nousresearch.com/docs/zh-Hans/getting-started/quickstart",
            "output": {"formats": ["markdown"]}
        })
    ],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)

data = json.loads(result.stdout)
raw = data['data']['markdown']

# Clean up broken chars
import re
cleaned = re.sub(r'[^\x20-\x7e一-鿿　-〿＀-￯\r\n\t]', '', raw)
# Remove navigation boilerplate (sidebar, footer, TOC)
# Keep from "# Quickstart" onward
idx = cleaned.find('# Quickstart')
if idx > 0:
    cleaned = cleaned[idx:]

# Split into chunks for translation (qwen-plus has context limits)
MAX_CHUNK = 3000
chunks = []
current = ''
for line in cleaned.split('\n'):
    if len(current) + len(line) + 1 > MAX_CHUNK:
        chunks.append(current)
        current = line
    else:
        current += ('\n' + line) if current else line
if current:
    chunks.append(current)

print(f'共 {len(chunks)} 个片段')

translated_parts = []
for i, chunk in enumerate(chunks):
    print(f'翻译片段 {i+1}/{len(chunks)} ({len(chunk)} 字)...')
    resp = Generation.call(
        model='qwen-plus',
        messages=[
            {
                'role': 'system',
                'content': '你是一个技术翻译。将以下英文 Markdown 文档翻译为简体中文。保留所有 Markdown 格式、代码块、链接和命令。只输出翻译结果，不要加说明。'
            },
            {'role': 'user', 'content': chunk}
        ],
        result_format='message'
    )
    if resp.status_code == 200:
        translated = resp.output.choices[0].message.content
        translated_parts.append(translated)
    else:
        print(f'片段 {i+1} 翻译失败: {resp}')
        translated_parts.append(chunk)

output = '\n\n---\n\n'.join(translated_parts)
output_path = os.path.join(os.path.dirname(__file__), '..', 'video_to_text', 'hermes', 'Quickstart_zh.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(output)
print(f'翻译完成, 已保存: {len(output)} 字')
