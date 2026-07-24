# scrape-and-translate

Scrape a webpage using xcrawl API, then translate the content to Chinese using DashScope LLM.

## Usage

```
/scrape-and-translate <url> [output_dir]
```

If `output_dir` is not specified, defaults to current directory. Output filename is derived from the URL path.

## API Configuration

- **xcrawl**: `xc-t5wyO5va9I5UMZKNFrD0vADZCM0z2rlwcpVtO6MnvaKxgFZg`
- **DashScope**: uses `dashscope` package, API key from project `video.py`

## Steps

1. **Scrape** the URL using xcrawl:

```bash
curl -s -X POST 'https://run.xcrawl.com/v1/scrape' \
  -H 'Authorization: Bearer xc-t5wyO5va9I5UMZKNFrD0vADZCM0z2rlwcpVtO6MnvaKxgFZg' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "<URL>",
    "output": {
      "formats": ["markdown"]
    }
  }'
```

2. **Extract markdown** from the JSON response (`data.markdown`) and save to `<output_dir>/<title>.md`. Clean surrogate characters with `.encode('utf-8', errors='replace').decode('utf-8')`.

3. **Translate** the English content to Chinese using DashScope `qwen-plus`:

```python
import dashscope
from dashscope import Generation
from http import HTTPStatus

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
dashscope.api_key = 'sk-e7742091eeaa427880f0765456e6b2ae'

system_prompt = '''你是一个专业翻译。请将以下英文技术文档翻译为简体中文。要求：
1. 保留所有 Markdown 格式（标题、代码块、表格、链接等）
2. 翻译技术术语时保留英文原名（如 CLI、TUI、MCP、OAuth、API 等）
3. 删除导航、侧边栏、页脚等无关内容（如跳转到主内容、Docs、Skills、Community、More、Built by 等）
4. 只输出翻译后的正文，不要任何前言或解释
5. 保持原有的标题层级和结构'''

resp = Generation.call(
    model='qwen-plus',
    messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': <markdown_content>}
    ],
    result_format='message'
)

if resp.status_code == HTTPStatus.OK:
    translated = resp.output.choices[0].message.content
    # save to <output_dir>/<title>_中文.md
```

4. Save translated content to `<output_dir>/<title>_中文.md`.
