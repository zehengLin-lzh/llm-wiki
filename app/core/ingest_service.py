from __future__ import annotations

import random
import string
from datetime import datetime, timezone

import structlog
import yaml

from app.core.file_ops import FileOps
from app.ingestors.base import IngestResult
from app.ingestors.markdown import MarkdownIngestor
from app.ingestors.pdf import PDFIngestor
from app.ingestors.text import TextIngestor
from app.ingestors.url import URLIngestor

log = structlog.get_logger()


class IngestService:
    """Unified entry point for all ingest operations."""

    def __init__(self, file_ops: FileOps, machine_name: str = ""):
        self.file_ops = file_ops
        self.machine_name = machine_name
        self._url = URLIngestor()
        self._pdf = PDFIngestor()
        self._markdown = MarkdownIngestor()
        self._text = TextIngestor()

    def _generate_id(self) -> str:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"raw_{ts}_{rand}"

    def _build_frontmatter(
        self, raw_id: str, result: IngestResult, tags: list[str] | None = None
    ) -> str:
        fm = {
            "id": raw_id,
            "source_type": result.source_type,
            **result.frontmatter,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "source_machine": self.machine_name,
            "compiled": False,
            "compile_provider": None,
            "tags": tags or [],
        }
        return "---\n" + yaml.dump(fm, default_flow_style=False, allow_unicode=True) + "---\n\n"

    async def ingest_url(
        self, url: str, subdir: str = "personal", tags: list[str] | None = None
    ) -> dict:
        """Ingest a URL."""
        result = await self._url.ingest(url)
        return await self._save(result, subdir, tags)

    async def ingest_pdf(
        self, filename: str, data: bytes, subdir: str = "personal", tags: list[str] | None = None
    ) -> dict:
        """Ingest a PDF file."""
        result = await self._pdf.ingest((filename, data))
        return await self._save(result, subdir, tags)

    async def ingest_markdown(
        self, filename: str, content: str, subdir: str = "personal", tags: list[str] | None = None
    ) -> dict:
        """Ingest a markdown file."""
        result = await self._markdown.ingest((filename, content))
        return await self._save(result, subdir, tags)

    async def ingest_text(
        self, filename: str, content: str, subdir: str = "personal", tags: list[str] | None = None
    ) -> dict:
        """Ingest plain text."""
        result = await self._text.ingest((filename, content))
        return await self._save(result, subdir, tags)

    async def ingest_file(
        self, filename: str, data: bytes, subdir: str = "personal", tags: list[str] | None = None
    ) -> dict:
        """Auto-detect file type and ingest."""
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return await self.ingest_pdf(filename, data, subdir, tags)
        elif lower.endswith(".md") or lower.endswith(".markdown"):
            content = data.decode("utf-8", errors="replace")
            return await self.ingest_markdown(filename, content, subdir, tags)
        else:
            # Treat as plain text
            content = data.decode("utf-8", errors="replace")
            return await self.ingest_text(filename, content, subdir, tags)

    async def _save(
        self, result: IngestResult, subdir: str, tags: list[str] | None
    ) -> dict:
        raw_id = self._generate_id()
        frontmatter = self._build_frontmatter(raw_id, result, tags)
        full_content = frontmatter + result.content

        path = self.file_ops.write_raw(
            subdir=subdir,
            filename=result.suggested_filename,
            content=full_content,
            reason=f"new {result.source_type} ingest",
        )

        rel_path = str(path.relative_to(self.file_ops.data_path))
        log.info(
            "ingest.saved",
            id=raw_id,
            source_type=result.source_type,
            path=rel_path,
        )

        return {
            "id": raw_id,
            "source_type": result.source_type,
            "raw_path": rel_path,
            "filename": result.suggested_filename,
        }
