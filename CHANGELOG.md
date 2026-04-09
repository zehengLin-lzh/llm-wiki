# Changelog

## [Unreleased]

### Phase 8: E2E Testing + Documentation (2026-04-09)
- **Added** `tests/test_providers.py` — 10 tests: provider init, probe, switch, fallback, message conversion
- **Added** `tests/test_compiler.py` — 14 tests: tool execution, frontmatter parsing, wiki structure
- **Added** `tests/test_e2e.py` — 16 tests: ingest lifecycle, lint lifecycle, snapshot lifecycle, full cycle
- **Updated** `README.md` — complete documentation: architecture, features, API reference, config guide
- **Total**: 60 tests, all passing

### Phase 7: Snapshot + Lint Worker (2026-04-09)
- **Added** `app/core/snapshot.py` — `SnapshotManager`: create/list/prune data snapshots
  - Auto-snapshot on startup if last snapshot > 24h old
  - Prune keeps most recent N snapshots (configurable, default 3)
- **Added** `app/core/lint.py` — `LintWorker`: 3 checks + markdown report generation
  - Orphan pages (no incoming links)
  - Dead links (point to non-existent files)
  - Missing summaries (raw files without wiki summary)
  - Reports saved to `wiki/_reports/{date}-lint.md`
- **Added** API endpoints: `POST /api/snapshot/create`, `GET /api/snapshot/list`, `POST /api/lint/run`, `GET /api/lint/latest`
- **Added** Settings tab: "Create Snapshot" + "Run Lint" buttons, snapshot list display

### Phase 6: Full Frontend — Wiki Browser + Settings (2026-04-09)
- **Added** `app/api/wiki.py` — `GET /api/wiki/tree`, `/api/wiki/file`, `/api/wiki/rendered` endpoints
- **Added** Three-column layout: wiki sidebar (left) + chat (center) + ingest/settings tabs (right)
- **Added** Wiki tree browser: expandable directory tree, click to view rendered file
- **Added** Wiki viewer: overlay panel with rendered markdown, clickable internal links
- **Added** Tab system: Ingest tab + Settings tab in right sidebar
- **Added** Settings tab: provider list, radio switch, test button, system info
- **Skipped** Alpine.js/Pico.css — vanilla JS stays lean and sufficient
- Server-side markdown → HTML rendering with heading, list, code, link support

### Phase 5: Query Engine + Chat UI (2026-04-09)
- **Added** `app/core/query_engine.py` — `QueryEngine` with read-only tool-call loop, yields `QueryEvent` stream
- **Added** `app/api/chat.py` — WebSocket endpoint `/ws/chat` for real-time chat
- **Added** Chat UI: two-panel layout (chat left, tools/ingest right), streaming bubbles, tool call indicators
- **Fixed** `app/llm/ollama.py` — message format conversion (Claude-style → OpenAI-style) for multi-round tool calls
- Query tools are read-only: read_wiki_file, list_wiki_directory, grep_wiki
- LLM cites wiki files in answers `[wiki/path/file.md]`
- Chat history maintained client-side, sent with each message for context

### Phase 4: Compiler — Raw to Wiki (2026-04-09)
- **Added** `app/llm/tools.py` — COMPILER_TOOLS (read/list/create/update/append wiki files) + QUERY_TOOLS (read-only)
- **Added** `app/core/compiler.py` — `Compiler` class with LLM tool-call loop (up to 20 rounds)
  - Reads raw source + schema + wiki state, then LLM decides what pages to create/update
  - Prompt injection defense: raw content treated as data, not instructions
  - Auto-marks raw frontmatter as `compiled: true` on success, `compile_error` on failure
- **Added** Schema templates: `coding-knowledge.md`, `research-notes.md`, `blank.md`
- **Updated** `app/api/ingest.py` — background compilation triggered after each ingest
- **Updated** `app/main.py` — auto-copies coding-knowledge schema template on first run
- Tested: ingest text about FastAPI → compiler generates index.md, summary, entity page with cross-refs

### Phase 3: Ingest Pipeline (2026-04-09)
- **Added** `app/ingestors/` — 4 ingestors: URL (trafilatura), PDF (pymupdf), Markdown, Text
- **Added** `app/core/ingest_service.py` — unified ingest entry point with auto ID generation and YAML frontmatter
- **Added** `app/api/ingest.py` — API endpoints: `POST /api/ingest/url`, `/api/ingest/file`, `/api/ingest/text`
- **Added** Frontend drop zone: drag & drop files, paste URL, subdirectory selector, ingest history
- **Added** `pyyaml` dependency for frontmatter serialization
- Each ingested file gets: unique ID, source metadata, machine name, `compiled: false` status
- All ingests auto-commit to the data/ git repo

### Phase 2: File Operations + Git Version Control (2026-04-09)
- **Added** `app/core/file_ops.py` — `FileOps` class with controlled read/write for raw and wiki files
  - Raw files are append-only (RawImmutableError on overwrite attempt)
  - Wiki files support full CRUD (create, read, update, delete)
  - All mutations auto-commit to a git repo inside `data/`
  - `grep_wiki()` for full-text search across wiki files
  - `wiki_tree()` for directory structure as JSON
  - Path traversal protection, filename sanitization
- **Added** `tests/test_file_ops.py` — 20 tests covering raw immutability, wiki CRUD, git commits, grep, schema
- **Updated** `app/main.py` — FileOps initialized on startup
- **Fixed** `pyproject.toml` — dev dependencies moved to `[dependency-groups]` for uv compatibility

### Phase 1: LLM Provider Abstraction Layer (2026-04-09)
- **Added** `app/llm/base.py` — `BaseLLMProvider` ABC with `available()`, `complete()`, `tool_call()`, `stream()`
- **Added** `app/llm/claude.py` — Claude API provider via Anthropic SDK (configurable model, default Sonnet 4.6)
- **Added** `app/llm/ollama.py` — Ollama REST provider via httpx (configurable model, default qwen3:8b)
- **Added** `app/llm/router.py` — `ProviderRouter` with startup probe, runtime switch, auto-fallback
- **Added** `app/schemas/models.py` — Pydantic models: ToolCall, ToolCallResult, ProviderStatus
- **Added** API endpoints: `GET /api/settings`, `POST /api/settings/provider`, `GET /api/test-llm`
- **Updated** Frontend: status bar with provider indicator + switch radio buttons + test button

### Phase 0: Project Skeleton + Config System (2026-04-09)
- **Added** FastAPI application with health endpoint and static file serving
- **Added** Config system: pydantic-settings + config.toml + .env hierarchy
- **Added** structlog logging setup
- **Added** Retro CMD-style frontend (black bg, green text, monospace)
- **Added** `start.command` double-click launcher for macOS
- **Added** Auto-creation of `data/` directory structure on startup
