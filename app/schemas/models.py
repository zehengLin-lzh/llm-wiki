from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# --- LLM Models ---


class ToolCall(BaseModel):
    """A single tool call from the LLM."""

    id: str
    name: str
    input: dict[str, Any]


class ToolCallResult(BaseModel):
    """Result from a tool_call request to the LLM."""

    tool_calls: list[ToolCall] = []
    text: str = ""
    stop_reason: str = ""
    usage: TokenUsage | None = None


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderStatus(BaseModel):
    name: str
    model: str
    available: bool
    status_message: str


class ProvidersInfo(BaseModel):
    current: str
    providers: list[ProviderStatus]
