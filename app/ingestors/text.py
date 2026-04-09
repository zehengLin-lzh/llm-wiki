from __future__ import annotations

import re

import structlog

from app.ingestors.base import IngestResult

log = structlog.get_logger()


class TextIngestor:
    source_type = "text"

    async def ingest(self, source: tuple[str, str]) -> IngestResult:
        """Ingest plain text from (filename, content)."""
        filename, content = source
        log.info("ingestor.text.start", filename=filename)

        # Wrap plain text in markdown
        title = re.sub(r"\.\w+$", "", filename)
        body = f"# {title}\n\n{content}"
        slug = self._slugify(title)

        frontmatter = {
            "source_type": "text",
            "original_filename": filename,
        }

        return IngestResult(
            content=body,
            suggested_filename=slug,
            frontmatter=frontmatter,
            source_type="text",
        )

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", "-", text).strip("-")
        return text[:80] if text else "untitled"
