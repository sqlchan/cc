"""批量抓取翻译 Hermes Agent 文档"""
import os
import re
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import dashscope
from dashscope import Generation

dashscope.api_key = 'sk-e7742091eeaa427880f0765456e6b2ae'
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

XCRAWL_API_URL = 'https://run.xcrawl.com/v1/scrape'
XCRAWL_AUTH = 'Bearer xc-t5wyO5va9I5UMZKNFrD0vADZCM0z2rlwcpVtO6MnvaKxgFZg'

MAX_WORKERS = 5
MAX_CHUNK = 3000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'harmes')


def url_to_filename(url):
    """Convert URL path to a safe filename."""
    path = urlparse(url).path.strip('/')
    name = path.replace('/', '_')
    if not name:
        name = 'index'
    return f"{name}.md"


def scrape(url):
    """Scrape a URL via xcrawl, return cleaned markdown."""
    result = subprocess.run(
        [
            'curl', '-s', '-X', 'POST', XCRAWL_API_URL,
            '-H', f'Authorization: {XCRAWL_AUTH}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "url": url,
                "output": {"formats": ["markdown"]}
            })
        ],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120
    )
    data = json.loads(result.stdout)
    raw = data['data']['markdown']
    cleaned = re.sub(r'[^\x20-\x7e一-鿿 -〿＀-￯\r\n\t]', '', raw)
    return cleaned


def translate(markdown_text):
    """Translate markdown to Chinese via qwen-plus."""
    chunks = []
    current = ''
    for line in markdown_text.split('\n'):
        if len(current) + len(line) + 1 > MAX_CHUNK:
            chunks.append(current)
            current = line
        else:
            current += ('\n' + line) if current else line
    if current:
        chunks.append(current)

    translated_parts = []
    for i, chunk in enumerate(chunks):
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
            translated_parts.append(resp.output.choices[0].message.content)
        else:
            print(f'  片段 {i+1} 翻译失败: {resp}')
            translated_parts.append(chunk)

    return '\n\n---\n\n'.join(translated_parts)


def process_url(url):
    """Scrape + translate one URL, save to output dir."""
    filename = url_to_filename(url)
    out_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(out_path):
        return f"SKIP {filename} (already exists)"

    print(f"START {url}")
    try:
        markdown = scrape(url)
        print(f"  Scraped {len(markdown)} chars -> {filename}")
        translated = translate(markdown)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(translated)
        return f"DONE  {filename} ({len(translated)} chars)"
    except Exception as e:
        return f"FAIL  {url} -> {e}"


def main():
    urls_file = os.path.join(os.path.dirname(__file__), 'urls.txt')
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"共 {len(urls)} 个 URL，并行度 {MAX_WORKERS}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_url, url): url for url in urls}
        for future in as_completed(futures):
            print(future.result())


if __name__ == '__main__':
    main()
