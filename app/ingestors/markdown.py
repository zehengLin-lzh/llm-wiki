from __future__ import annotations

import re

import structlog

from app.ingestors.base import IngestResult

log = structlog.get_logger()


class MarkdownIngestor:
    source_type = "markdown"

    async def ingest(self, source: tuple[str, str]) -> IngestResult:
        """Ingest markdown content from (filename, content)."""
        filename, content = source
        log.info("ingestor.markdown.start", filename=filename)

        # Strip existing frontmatter if present (we'll add our own)
        body = self._strip_frontmatter(content)

        title = self._extract_title(body, filename)
        slug = self._slugify(title)

        frontmatter = {
            "source_type": "markdown",
            "original_filename": filename,
        }

        return IngestResult(
            content=body,
            suggested_filename=slug,
            frontmatter=frontmatter,
            source_type="markdown",
        )

    def _strip_frontmatter(self, content: str) -> str:
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

    def _extract_title(self, content: str, filename: str) -> str:
        for line in content.splitlines()[:10]:
            if line.strip().startswith("# "):
                return line.strip()[2:].strip()
        return re.sub(r"\.md$", "", filename)

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", "-", text).strip("-")
        return text[:80] if text else "untitled"
