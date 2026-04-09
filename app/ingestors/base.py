from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class IngestResult(BaseModel):
    """Result of an ingest operation."""

    content: str  # markdown body
    suggested_filename: str
    frontmatter: dict[str, Any]
    source_type: str


@runtime_checkable
class Ingestor(Protocol):
    """Protocol for all ingestors."""

    source_type: str

    async def ingest(self, source: Any) -> IngestResult: ...
