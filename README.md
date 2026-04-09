# Personal LLM Wiki

Local-first personal knowledge base powered by LLM compilation. Based on Andrej Karpathy's LLM Wiki concept.

## Core Idea

Instead of real-time RAG (vector search on every query), the LLM acts as a **compiler**: raw sources are pre-processed into structured markdown wiki pages. Queries read the compiled wiki directly.

## Architecture

```
Raw Sources (read-only)  -->  LLM Compiler  -->  Wiki (LLM-maintained)
                                    ^
                                    |
                              Schema (user rules)
```

- **Raw**: Ingested files (URLs, PDFs, markdown, text). Immutable once written.
- **Wiki**: Structured markdown pages maintained by LLM. Concepts, entities, summaries, index.
- **Schema**: User-defined rules for how the wiki should be organized.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **LLM Providers**: Claude API (Anthropic SDK) + Ollama (local, qwen3:8b)
- **Frontend**: HTML + vanilla JS (Alpine.js in later phases)
- **Storage**: Markdown files + Git auto-versioning
- **Package Manager**: uv

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/zehengLin-lzh/llm-wiki.git
cd llm-wiki

# 2. Copy config templates
cp .env.example .env        # Add your ANTHROPIC_API_KEY
cp config.toml.example config.toml

# 3. Install and run
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 7823

# Or double-click start.command on macOS
```

Then open http://localhost:7823.

## Development

```bash
# Run tests
uv sync --group dev
uv run pytest tests/ -v
```

## Current Status

See [CHANGELOG.md](CHANGELOG.md) for detailed progress.