from __future__ import annotations

import json
from typing import AsyncIterator

import httpx
import structlog

from app.llm.base import BaseLLMProvider
from app.schemas.models import TokenUsage, ToolCall, ToolCallResult

log = structlog.get_logger()


class OllamaProvider(BaseLLMProvider):
    """Ollama REST API provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:8b"):
        self.name = "ollama"
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _client(self, timeout: float = 60) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def available(self) -> tuple[bool, str]:
        try:
            async with self._client(timeout=5) as client:
                resp = await client.get("/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                # Check if our target model is available (match with or without tag)
                found = any(
                    self.model in m or m.startswith(self.model.split(":")[0])
                    for m in models
                )
                if found:
                    return True, f"OK (model: {self.model})"
                return False, f"Model {self.model} not found. Available: {models}"
        except httpx.ConnectError:
            return False, "Ollama not running (connection refused)"
        except httpx.TimeoutException:
            return False, "Timeout (5s)"
        except Exception as e:
            return False, f"Error: {e}"

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> str:
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        async with self._client(timeout=120) as client:
            resp = await client.post(
                "/api/chat",
                json={"model": self.model, "messages": msgs, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def tool_call(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
    ) -> ToolCallResult:
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        # Convert Anthropic-style tools to Ollama/OpenAI-style
        ollama_tools = []
        for tool in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })

        async with self._client(timeout=120) as client:
            resp = await client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": msgs,
                    "tools": ollama_tools,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        text = msg.get("content", "") or ""
        tool_calls = []

        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", f"ollama_{len(tool_calls)}"),
                    name=fn.get("name", ""),
                    input=args,
                )
            )

        # Estimate token usage from Ollama response
        usage = None
        if "prompt_eval_count" in data or "eval_count" in data:
            usage = TokenUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            )

        return ToolCallResult(
            tool_calls=tool_calls,
            text=text,
            stop_reason="tool_calls" if tool_calls else "stop",
            usage=usage,
        )

    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> AsyncIterator[str]:
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        async with self._client(timeout=120) as client:
            async with client.stream(
                "POST",
                "/api/chat",
                json={"model": self.model, "messages": msgs, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
