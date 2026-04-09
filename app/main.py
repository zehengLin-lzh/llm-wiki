from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import AppState, load_config
from app.llm.router import ProviderRouter
from app.logging_setup import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "web"

setup_logging()
log = structlog.get_logger()

config = load_config(PROJECT_ROOT)
config.ensure_data_dirs()

state = AppState(config.data_path / ".state.json")
state.update(
    last_machine=config.current_machine,
    last_started_at=datetime.now(timezone.utc).isoformat(),
)

# LLM Provider Router
api_key = config.llm.claude.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
router = ProviderRouter(
    claude_api_key=api_key,
    claude_model=config.llm.claude.model,
    ollama_base_url=config.llm.ollama.base_url,
    ollama_model=config.llm.ollama.model,
    primary=config.llm.primary,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: probe all providers
    await router.probe_all()
    log.info("app.startup.complete", providers=router.get_info().model_dump())
    yield


app = FastAPI(title="Personal LLM Wiki", version="0.1.0", lifespan=lifespan)

# Static files must be mounted AFTER app creation but works fine here
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

log.info(
    "app.startup",
    machine=config.current_machine,
    data_dir=str(config.data_path),
    primary_provider=config.llm.primary,
)


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health():
    info = router.get_info()
    return {
        "status": "ok",
        "machine": config.current_machine,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(config.data_path),
        "provider": info.current,
        "providers": [p.model_dump() for p in info.providers],
    }


@app.get("/api/settings")
async def get_settings():
    info = router.get_info()
    return {
        "provider": info.current,
        "providers": [p.model_dump() for p in info.providers],
        "state": state.data,
    }


@app.post("/api/settings/provider")
async def switch_provider(body: dict):
    name = body.get("provider", "")
    try:
        status = await router.switch_to(name)
        state.update(provider_preference=name)
        return {"ok": True, "provider": status.model_dump()}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/test-llm")
async def test_llm():
    """Quick test: ask the current provider a simple question."""
    provider = await router.get_provider()
    try:
        result = await provider.complete(
            messages=[{"role": "user", "content": "Say 'hello' in one word."}],
        )
        return {
            "ok": True,
            "provider": provider.name,
            "model": provider.model,
            "response": result,
        }
    except Exception as e:
        return {
            "ok": False,
            "provider": provider.name,
            "model": provider.model,
            "error": str(e),
        }
