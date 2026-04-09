from __future__ import annotations

import re
from urllib.parse import urlparse

import structlog
import trafilatura

from app.ingestors.base import IngestResult

log = structlog.get_logger()


class URLIngestor:
    source_type = "url"

    async def ingest(self, source: str) -> IngestResult:
        """Ingest a URL, extracting content as markdown."""
        url = source.strip()
        log.info("ingestor.url.start", url=url)

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"Failed to fetch URL: {url}")

        content = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_links=True,
            include_tables=True,
        )
        if not content:
            raise ValueError(f"Failed to extract content from: {url}")

        # Extract title from content or URL
        title = self._extract_title(content, url)
        filename = self._slugify(title)

        frontmatter = {
            "source_type": "url",
            "source_url": url,
        }

        log.info("ingestor.url.done", url=url, filename=filename, length=len(content))
        return IngestResult(
            content=content,
            suggested_filename=filename,
            frontmatter=frontmatter,
            source_type="url",
        )

    def _extract_title(self, content: str, url: str) -> str:
        # Try first markdown heading
        for line in content.splitlines()[:10]:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fallback: use URL path
        parsed = urlparse(url)
        path = parsed.path.strip("/").split("/")[-1] if parsed.path.strip("/") else parsed.netloc
        return path.replace("-", " ").replace("_", " ").split(".")[0]

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", "-", text).strip("-")
        return text[:80] if text else "untitled"
