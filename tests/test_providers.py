"""Tests for LLM provider abstraction layer."""

from __future__ import annotations

import pytest

from app.llm.claude import ClaudeProvider
from app.llm.ollama import OllamaProvider
from app.llm.router import ProviderRouter
from app.schemas.models import ToolCall


class TestClaudeProvider:
    def test_init_without_key(self):
        provider = ClaudeProvider(api_key="", model="claude-sonnet-4-6-20250514")
        assert provider.name == "claude"
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_available_no_key(self):
        provider = ClaudeProvider(api_key="", model="claude-sonnet-4-6-20250514")
        ok, msg = await provider.available()
        assert not ok
        assert "No API key" in msg

    @pytest.mark.asyncio
    async def test_available_invalid_key(self):
        provider = ClaudeProvider(api_key="sk-ant-invalid", model="claude-sonnet-4-6-20250514")
        ok, msg = await provider.available()
        assert not ok


class TestOllamaProvider:
    def test_init(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3:8b")
        assert provider.name == "ollama"
        assert provider.model == "qwen3:8b"

    def test_convert_messages_simple(self):
        provider = OllamaProvider()
        msgs = [{"role": "user", "content": "hello"}]
        result = provider._convert_messages(msgs)
        assert result == msgs

    def test_convert_messages_tool_use(self):
        """Claude-style tool_use messages should be converted to OpenAI style."""
        provider = OllamaProvider()
        msgs = [
            {"role": "user", "content": "test"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {"type": "tool_use", "id": "t1", "name": "read_wiki_file", "input": {"path": "index.md"}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "# Index\n..."},
                ],
            },
        ]
        result = provider._convert_messages(msgs)
        assert len(result) == 3
        # Assistant message should have tool_calls
        assert "tool_calls" in result[1]
        assert result[1]["tool_calls"][0]["function"]["name"] == "read_wiki_file"
        # Tool result should be role=tool
        assert result[2]["role"] == "tool"
        assert "Index" in result[2]["content"]


class TestProviderRouter:
    @pytest.mark.asyncio
    async def test_probe_and_info(self):
        router = ProviderRouter(
            claude_api_key="",
            claude_model="claude-sonnet-4-6-20250514",
            ollama_base_url="http://localhost:99999",
            ollama_model="nonexistent",
            primary="claude",
        )
        await router.probe_all()
        info = router.get_info()
        assert info.current == "claude"
        assert len(info.providers) == 2

    @pytest.mark.asyncio
    async def test_switch_to(self):
        router = ProviderRouter(
            claude_api_key="",
            claude_model="claude-sonnet-4-6-20250514",
            ollama_base_url="http://localhost:99999",
            ollama_model="nonexistent",
            primary="claude",
        )
        await router.switch_to("ollama")
        assert router.primary_name == "ollama"

    @pytest.mark.asyncio
    async def test_switch_to_invalid(self):
        router = ProviderRouter(
            claude_api_key="",
            claude_model="test",
            ollama_base_url="http://localhost:99999",
            ollama_model="test",
        )
        with pytest.raises(ValueError):
            await router.switch_to("openai")

    @pytest.mark.asyncio
    async def test_fallback(self):
        router = ProviderRouter(
            claude_api_key="",
            claude_model="test",
            ollama_base_url="http://localhost:99999",
            ollama_model="test",
            primary="claude",
        )
        await router.probe_all()
        # Both unavailable, should return primary anyway
        provider = await router.get_provider()
        assert provider.name == "claude"
