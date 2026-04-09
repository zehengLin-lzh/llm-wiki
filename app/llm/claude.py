from __future__ import annotations

import asyncio
from typing import AsyncIterator

import anthropic
import structlog

from app.llm.base import BaseLLMProvider
from app.schemas.models import TokenUsage, ToolCall, ToolCallResult

log = structlog.get_logger()


class ClaudeProvider(BaseLLMProvider):
    """Claude API provider using the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6-20250514"):
        self.name = "claude"
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None

    async def available(self) -> tuple[bool, str]:
        if not self._client:
            return False, "No API key configured"
        try:
            resp = await asyncio.wait_for(
                self._client.messages.create(
                    model=self.model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                ),
                timeout=10,
            )
            return True, f"OK (model: {self.model})"
        except asyncio.TimeoutError:
            return False, "Timeout (10s)"
        except anthropic.AuthenticationError:
            return False, "Invalid API key"
        except anthropic.APIConnectionError as e:
            return False, f"Connection error: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        resp = await self._client.messages.create(**kwargs)
        return "".join(
            block.text for block in resp.content if block.type == "text"
        )

    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
    ) -> ToolCallResult:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
            "tools": tools,
        }
        if system:
            kwargs["system"] = system

        resp = await self._client.messages.create(**kwargs)

        tool_calls = []
        text_parts = []
        for block in resp.content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=block.input)
                )
            elif block.type == "text":
                text_parts.append(block.text)

        return ToolCallResult(
            tool_calls=tool_calls,
            text="".join(text_parts),
            stop_reason=resp.stop_reason or "",
            usage=TokenUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
        )

    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
