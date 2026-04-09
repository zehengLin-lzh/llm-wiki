from __future__ import annotations

import structlog

from app.llm.base import BaseLLMProvider
from app.llm.claude import ClaudeProvider
from app.llm.ollama import OllamaProvider
from app.schemas.models import ProviderStatus, ProvidersInfo

log = structlog.get_logger()


class ProviderRouter:
    """Routes LLM requests to the active provider with automatic fallback."""

    def __init__(
        self,
        claude_api_key: str,
        claude_model: str,
        ollama_base_url: str,
        ollama_model: str,
        primary: str = "claude",
    ):
        self._providers: dict[str, BaseLLMProvider] = {
            "claude": ClaudeProvider(api_key=claude_api_key, model=claude_model),
            "ollama": OllamaProvider(base_url=ollama_base_url, model=ollama_model),
        }
        self._primary_name = primary
        self._statuses: dict[str, ProviderStatus] = {}

    @property
    def primary_name(self) -> str:
        return self._primary_name

    @property
    def primary(self) -> BaseLLMProvider:
        return self._providers[self._primary_name]

    @property
    def fallback(self) -> BaseLLMProvider | None:
        for name, provider in self._providers.items():
            if name != self._primary_name:
                return provider
        return None

    async def probe_all(self) -> dict[str, ProviderStatus]:
        """Probe all providers and cache their status."""
        for name, provider in self._providers.items():
            ok, msg = await provider.available()
            self._statuses[name] = ProviderStatus(
                name=name,
                model=provider.model,
                available=ok,
                status_message=msg,
            )
            log.info(
                "provider.probe",
                provider=name,
                model=provider.model,
                available=ok,
                message=msg,
            )
        return self._statuses

    async def switch_to(self, name: str) -> ProviderStatus:
        """Switch the primary provider."""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(self._providers.keys())}")
        self._primary_name = name
        # Re-probe the new primary
        ok, msg = await self._providers[name].available()
        self._statuses[name] = ProviderStatus(
            name=name,
            model=self._providers[name].model,
            available=ok,
            status_message=msg,
        )
        log.info("provider.switched", provider=name, available=ok)
        return self._statuses[name]

    async def get_provider(self) -> BaseLLMProvider:
        """Get the current provider, falling back if primary is unavailable."""
        primary = self.primary
        status = self._statuses.get(self._primary_name)

        # If we haven't probed yet or primary is available, use it
        if status is None or status.available:
            return primary

        # Primary is known unavailable, try fallback
        fb = self.fallback
        if fb:
            fb_status = self._statuses.get(fb.name)
            if fb_status and fb_status.available:
                log.warning(
                    "provider.fallback",
                    primary=self._primary_name,
                    fallback=fb.name,
                )
                return fb

        # Both unavailable, return primary anyway (let it fail with a real error)
        return primary

    def get_info(self) -> ProvidersInfo:
        """Get current provider information."""
        return ProvidersInfo(
            current=self._primary_name,
            providers=list(self._statuses.values()),
        )
