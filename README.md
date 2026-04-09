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

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| Package Manager | uv |
| Web Framework | FastAPI + Uvicorn |
| LLM (Cloud) | Claude API (Anthropic SDK) — Sonnet/Opus/Haiku |
| LLM (Local) | Ollama (qwen3:8b, qwen3:14b, etc.) |
| File Ingest | trafilatura (URLs), pymupdf (PDFs) |
| Version Control | GitPython (auto-commits in data/) |
| Frontend | Vanilla JS, no build tools |
| Config | pydantic-settings + TOML |
| Logging | structlog |

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

Open http://127.0.0.1:7823. The `data/` directory is auto-created on first run.

## Features

### Ingest
- **URL**: Paste a URL, article content is extracted as markdown
- **PDF**: Drag & drop, text extracted per page
- **Markdown/Text**: Direct upload or paste

Each ingested file gets a unique ID, YAML frontmatter, and a git commit.

### Compile
After ingest, the LLM compiler automatically:
1. Reads the raw source + schema + current wiki state
2. Creates a summary page in `wiki/summaries/`
3. Extracts entities and creates/updates pages in `wiki/entities/`
4. Updates `wiki/index.md` with new entries
5. All via tool calls — the LLM decides what pages to create

### Query
Chat with your wiki in the browser. The LLM:
- Reads wiki files via tools (read, list, grep)
- Cites sources in answers `[wiki/path/file.md]`
- Says "I don't know" when info isn't in the wiki

### Wiki Browser
Left sidebar shows the wiki directory tree. Click any file to view rendered content.

### Providers
- **Claude API**: Best quality, requires API key and internet
- **Ollama**: Local, free, works offline (qwen3:8b recommended)
- Switch providers and models at runtime from the Settings tab

### Maintenance
- **Snapshots**: Auto-created on startup, manual via Settings tab
- **Lint**: Detects orphan pages, dead links, missing summaries

## Project Structure

```
app/
  main.py              # FastAPI app, startup, all API routes
  config.py            # Config loading (TOML + .env)
  api/
    chat.py            # WebSocket /ws/chat
    ingest.py          # POST /api/ingest/{url,file,text}
    wiki.py            # GET /api/wiki/{tree,file,rendered}
  core/
    file_ops.py        # Controlled read/write + git auto-commit
    compiler.py        # Raw → wiki via LLM tool calls
    query_engine.py    # Wiki Q&A via LLM tool calls
    ingest_service.py  # Unified ingest entry point
    snapshot.py        # Data snapshots
    lint.py            # Wiki health checks
  llm/
    base.py            # BaseLLMProvider ABC
    claude.py          # Claude API implementation
    ollama.py          # Ollama REST implementation
    router.py          # Provider switching + fallback
    tools.py           # Tool definitions for compiler + query
  web/                 # Frontend (vanilla JS)
data/                  # Knowledge base (separate git repo, gitignored)
  raw/                 # Immutable source files
  wiki/                # LLM-maintained wiki pages
  schema.md            # User's organization rules
  .state.json          # System state
  .snapshots/          # Data snapshots
tests/                 # 60 tests
```

## Configuration

### .env
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### config.toml
```toml
[server]
host = "127.0.0.1"
port = 7823

[llm]
primary = "claude"  # or "ollama"

[llm.claude]
model = "claude-sonnet-4-6-20250514"

[llm.ollama]
base_url = "http://localhost:11434"
model = "qwen3:8b"
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run all tests (60 tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_file_ops.py -v
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | System status |
| GET | `/api/settings` | Current settings |
| POST | `/api/settings/provider` | Switch active provider |
| GET | `/api/models` | List available models |
| POST | `/api/settings/model` | Switch model for a provider |
| GET | `/api/test-llm` | Test current provider |
| POST | `/api/ingest/url` | Ingest a URL |
| POST | `/api/ingest/file` | Upload a file |
| POST | `/api/ingest/text` | Ingest text |
| GET | `/api/wiki/tree` | Wiki directory tree |
| GET | `/api/wiki/file?path=` | Raw wiki file content |
| GET | `/api/wiki/rendered?path=` | Rendered wiki file HTML |
| POST | `/api/snapshot/create` | Create data snapshot |
| GET | `/api/snapshot/list` | List snapshots |
| POST | `/api/lint/run` | Run lint checks |
| GET | `/api/lint/latest` | Get latest lint report |
| WS | `/ws/chat` | Chat WebSocket |

## See Also

- [CHANGELOG.md](CHANGELOG.md) — Detailed phase-by-phase progress
- Inspired by [Andrej Karpathy's LLM Wiki concept](https://x.com/karpathy)