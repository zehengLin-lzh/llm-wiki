# Schema: Coding Knowledge Base

## Purpose
This knowledge base accumulates cross-project coding habits, design decisions, pitfall records, and tool configurations.

## Entity Types
- **language**: Programming languages (Python, TypeScript, Rust, etc.)
- **tool**: Development tools (uv, Claude Code, Ollama, Tabby, etc.)
- **library**: Libraries/frameworks (FastAPI, LangGraph, Airflow, etc.)
- **pattern**: Design patterns or practices (7-stage pipeline, provider routing, etc.)
- **decision**: Technical decision records (why choose qwen3:8b over 14b)
- **pitfall**: Pitfall records (fzf-tab must load after compinit)

## Page Structure
- `concepts/` — general concepts and patterns
- `entities/` — specific tools, libraries, languages
- `summaries/` — one summary per raw file
- `_reports/` — lint reports (auto-generated)

## Compilation Conventions
- Each raw file generates one summary in `summaries/`
- Entities extracted from raw content update corresponding entity pages
- New concepts found create pages in `concepts/`
- All pages maintain Related links to connected topics
- `index.md` is the master directory — always keep it updated

## Query Conventions
- Start with `index.md` to navigate
- Entity queries check `entities/` first
- Concept queries check `concepts/` first
- Use grep as fallback for keyword search
