from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from pydantic import BaseModel

from app.core.compiler import Compiler
from app.core.ingest_service import IngestService
from app.llm.base import BaseLLMProvider
from app.llm.router import ProviderRouter

log = structlog.get_logger()

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# Will be set by main.py on startup
_ingest_service: IngestService | None = None
_compiler: Compiler | None = None
_provider_router: ProviderRouter | None = None


def init_ingest_router(
    ingest_service: IngestService,
    compiler: Compiler | None = None,
    provider_router: ProviderRouter | None = None,
) -> None:
    global _ingest_service, _compiler, _provider_router
    _ingest_service = ingest_service
    _compiler = compiler
    _provider_router = provider_router


def _svc() -> IngestService:
    assert _ingest_service is not None, "IngestService not initialized"
    return _ingest_service


async def _compile_background(raw_path_str: str) -> None:
    """Background task: compile a raw file into wiki pages."""
    if not _compiler or not _provider_router:
        log.warning("compile.skip", reason="compiler or router not configured")
        return
    try:
        provider = await _provider_router.get_provider()
        raw_path = Path(raw_path_str)
        result = await _compiler.compile_raw_file(raw_path, provider)
        if result.success:
            log.info("compile.background.done", operations=len(result.operations), summary=result.summary[:100])
        else:
            log.error("compile.background.failed", error=result.error)
    except Exception as e:
        log.error("compile.background.error", error=str(e))


class URLIngestRequest(BaseModel):
    url: str
    subdir: str = "personal"
    tags: list[str] = []


class TextIngestRequest(BaseModel):
    content: str
    filename: str = "note.txt"
    subdir: str = "personal"
    tags: list[str] = []


@router.post("/url")
async def ingest_url(req: URLIngestRequest, background_tasks: BackgroundTasks):
    try:
        result = await _svc().ingest_url(
            url=req.url, subdir=req.subdir, tags=req.tags
        )
        # Trigger background compilation
        raw_abs = _svc().file_ops.data_path / result["raw_path"]
        background_tasks.add_task(_compile_background, str(raw_abs))
        return {"ok": True, **result, "compiling": True}
    except Exception as e:
        log.error("ingest.url.error", error=str(e), url=req.url)
        return {"ok": False, "error": str(e)}


@router.post("/file")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subdir: str = Form("personal"),
    tags: str = Form(""),
):
    try:
        data = await file.read()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        result = await _svc().ingest_file(
            filename=file.filename or "upload",
            data=data,
            subdir=subdir,
            tags=tag_list,
        )
        raw_abs = _svc().file_ops.data_path / result["raw_path"]
        background_tasks.add_task(_compile_background, str(raw_abs))
        return {"ok": True, **result, "compiling": True}
    except Exception as e:
        log.error("ingest.file.error", error=str(e), filename=file.filename)
        return {"ok": False, "error": str(e)}


@router.post("/text")
async def ingest_text(req: TextIngestRequest, background_tasks: BackgroundTasks):
    try:
        result = await _svc().ingest_text(
            filename=req.filename,
            content=req.content,
            subdir=req.subdir,
            tags=req.tags,
        )
        raw_abs = _svc().file_ops.data_path / result["raw_path"]
        background_tasks.add_task(_compile_background, str(raw_abs))
        return {"ok": True, **result, "compiling": True}
    except Exception as e:
        log.error("ingest.text.error", error=str(e))
        return {"ok": False, "error": str(e)}
