from __future__ import annotations

import re
from pathlib import Path

import pymupdf
import structlog

from app.ingestors.base import IngestResult

log = structlog.get_logger()


class PDFIngestor:
    source_type = "pdf"

    async def ingest(self, source: tuple[str, bytes]) -> IngestResult:
        """Ingest a PDF from (filename, bytes)."""
        filename, data = source
        log.info("ingestor.pdf.start", filename=filename, size=len(data))

        doc = pymupdf.open(stream=data, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages.append(f"## Page {i + 1}\n\n{text.strip()}")
        doc.close()

        if not pages:
            raise ValueError(f"No text content extracted from PDF: {filename}")

        title = Path(filename).stem
        content = f"# {title}\n\n" + "\n\n---\n\n".join(pages)
        slug = self._slugify(title)

        frontmatter = {
            "source_type": "pdf",
            "original_filename": filename,
        }

        log.info("ingestor.pdf.done", filename=filename, pages=len(pages), length=len(content))
        return IngestResult(
            content=content,
            suggested_filename=slug,
            frontmatter=frontmatter,
            source_type="pdf",
        )

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", "-", text).strip("-")
        return text[:80] if text else "untitled"
