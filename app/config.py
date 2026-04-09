from __future__ import annotations

import json
import platform
import socket
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from pydantic import Field
from pydantic_settings import BaseSettings


def _load_toml(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path, "rb") as f:
            return tomllib.load(f)
    return {}


class ServerConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 7823


class ClaudeConfig(BaseSettings):
    model: str = "claude-sonnet-4-6-20250514"
    api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")


class OllamaConfig(BaseSettings):
    base_url: str = "http://localhost:11434"
    model: str = "qwen3:8b"


class LLMConfig(BaseSettings):
    primary: str = "claude"
    claude: ClaudeConfig = ClaudeConfig()
    ollama: OllamaConfig = OllamaConfig()


class SnapshotConfig(BaseSettings):
    retention: int = 3


class DataSettingsConfig(BaseSettings):
    auto_compile_on_ingest: bool = True
    lint_schedule: str = "daily"


class DataConfig(BaseSettings):
    base_dir: str = "data"
    snapshot: SnapshotConfig = SnapshotConfig()
    settings: DataSettingsConfig = DataSettingsConfig()


class AppConfig(BaseSettings):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    data: DataConfig = DataConfig()

    current_machine: str = ""

    model_config = {"env_prefix": "", "env_nested_delimiter": "__"}

    def __init__(self, config_path: Path | None = None, **kwargs: Any):
        toml_data = {}
        if config_path and config_path.exists():
            toml_data = _load_toml(config_path)

        # Flatten TOML into kwargs for pydantic-settings
        if "server" in toml_data:
            kwargs.setdefault("server", ServerConfig(**toml_data["server"]))
        if "llm" in toml_data:
            llm_raw = toml_data["llm"]
            claude_cfg = ClaudeConfig(**llm_raw.get("claude", {}))
            ollama_cfg = OllamaConfig(**llm_raw.get("ollama", {}))
            kwargs.setdefault(
                "llm",
                LLMConfig(
                    primary=llm_raw.get("primary", "claude"),
                    claude=claude_cfg,
                    ollama=ollama_cfg,
                ),
            )
        if "data" in toml_data:
            data_raw = toml_data["data"]
            kwargs.setdefault(
                "data",
                DataConfig(
                    base_dir=data_raw.get("base_dir", "data"),
                    snapshot=SnapshotConfig(**data_raw.get("snapshot", {})),
                    settings=DataSettingsConfig(**data_raw.get("settings", {})),
                ),
            )

        super().__init__(**kwargs)

        if not self.current_machine:
            self.current_machine = socket.gethostname()

    @property
    def data_path(self) -> Path:
        return Path(self.data.base_dir).resolve()

    def ensure_data_dirs(self) -> None:
        """Create data directory structure if missing."""
        dirs = [
            self.data_path,
            self.data_path / "raw" / "personal",
            self.data_path / "raw" / "work",
            self.data_path / "raw" / "shared",
            self.data_path / "wiki" / "concepts",
            self.data_path / "wiki" / "entities",
            self.data_path / "wiki" / "summaries",
            self.data_path / "wiki" / "_reports",
            self.data_path / ".snapshots",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


class AppState:
    """Manages data/.state.json."""

    def __init__(self, state_path: Path):
        self.path = state_path
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return self._default()

    def _default(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "last_machine": "",
            "last_started_at": "",
            "provider_preference": "claude",
            "stats": {
                "raw_count": 0,
                "wiki_count": 0,
                "last_lint_at": None,
            },
            "settings": {
                "snapshot_retention": 3,
                "auto_compile_on_ingest": True,
                "lint_schedule": "daily",
            },
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def update(self, **kwargs: Any) -> None:
        self._data.update(kwargs)
        self.save()

    def update_stats(self, **kwargs: Any) -> None:
        self._data.setdefault("stats", {}).update(kwargs)
        self.save()

    def update_settings(self, **kwargs: Any) -> None:
        self._data.setdefault("settings", {}).update(kwargs)
        self.save()

    @property
    def data(self) -> dict[str, Any]:
        return self._data


def load_config(project_root: Path | None = None) -> AppConfig:
    """Load config from config.toml + .env in project root."""
    if project_root is None:
        project_root = Path.cwd()

    config_path = project_root / "config.toml"
    return AppConfig(config_path=config_path)
