from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.schemas.models import ToolCallResult


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str
    model: str

    @abstractmethod
    async def available(self) -> tuple[bool, str]:
        """Check if the provider is available.

        Returns (is_available, status_message).
        """
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> str:
        """Send messages and return the complete response text."""
        ...

    @abstractmethod
    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
    ) -> ToolCallResult:
        """Send messages with tool definitions and return tool call result."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        ...
