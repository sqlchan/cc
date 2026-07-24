# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

Two features sharing DashScope (阿里云灵积) services:

1. **video_to_text/** — Video-to-Markdown transcription (ASR + LLM polish)
2. **scrape_translate/** — Web scraping + translation (xcrawl + LLM translate)

## Pipeline: video_to_text/

```
video file → extract audio (ffmpeg) → upload to DashScope → ASR transcription (fun-asr) → LLM text polishing (qwen-plus) → save .md
```

### Commands

```bash
# Single video
python video_to_text/video.py <video_path>

# Batch directory (concurrent, 3 workers) — skips videos that already have .md output
python video_to_text/video.py <directory_path>
```

### Architecture

- **`video.py`** — All logic in one file (~260 lines)
  - `extract_audio()` — ffmpeg subprocess to extract WAV
  - `upload_audio()` — DashScope Files API
  - `transcribe_audio()` — DashScope ASR (async task + wait)
  - `polish_text()` — DashScope Generation (LLM cleanup)
  - `video_to_text()` — orchestrates the pipeline for a single video
  - `process_directory()` — concurrent batch via `ThreadPoolExecutor(MAX_WORKERS=3)`
  - `safe_print()` — thread-safe print for concurrent output
  - `_strip_llm_wrapper()` — removes LLM-generated preamble/postamble

## Pipeline: scrape_translate/

```
URL → xcrawl scrape (markdown) → LLM translation (qwen-plus) → save .md
```

### video_to_text/ files

- **`video.py`** — Main script (single-file pipeline)
- **`video/`** — Input videos + output wav/txt/md
- **`hermes/`** — Hermes Agent tutorial videos + transcriptions + translated docs

### scrape_translate/ files

- **`translate.py`** — Scrapes a URL via xcrawl API, translates via qwen-plus
- **`pachong.txt`** — xcrawl API reference notes
- **`llm_res.py`** — Quick test script for multimodal LLM (qwen3.6-plus vision)

## Shared dependencies

- `dashscope` — Alibaba Cloud AI API (ASR + LLM)
- `ffmpeg` — system ffmpeg, or `imageio-ffmpeg` as fallback (video_to_text only)
- `requests` (transitive via dashscope)

## Important Notes

- API keys are hardcoded in source files — do not expose externally
- `polish_text()` uses a strict prompt that forbids rewriting/summarizing
- `process_directory()` uses `.md` existence check to skip already-converted videos
- All pipeline functions raise exceptions instead of `sys.exit()` to support concurrent execution
