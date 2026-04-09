from __future__ import annotations

import structlog
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.core.ingest_service import IngestService

log = structlog.get_logger()

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# Will be set by main.py on startup
_ingest_service: IngestService | None = None


def init_ingest_router(ingest_service: IngestService) -> None:
    global _ingest_service
    _ingest_service = ingest_service


def _svc() -> IngestService:
    assert _ingest_service is not None, "IngestService not initialized"
    return _ingest_service


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
async def ingest_url(req: URLIngestRequest):
    try:
        result = await _svc().ingest_url(
            url=req.url, subdir=req.subdir, tags=req.tags
        )
        return {"ok": True, **result}
    except Exception as e:
        log.error("ingest.url.error", error=str(e), url=req.url)
        return {"ok": False, "error": str(e)}


@router.post("/file")
async def ingest_file(
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
        return {"ok": True, **result}
    except Exception as e:
        log.error("ingest.file.error", error=str(e), filename=file.filename)
        return {"ok": False, "error": str(e)}


@router.post("/text")
async def ingest_text(req: TextIngestRequest):
    try:
        result = await _svc().ingest_text(
            filename=req.filename,
            content=req.content,
            subdir=req.subdir,
            tags=req.tags,
        )
        return {"ok": True, **result}
    except Exception as e:
        log.error("ingest.text.error", error=str(e))
        return {"ok": False, "error": str(e)}
