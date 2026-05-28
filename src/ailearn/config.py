from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    base_url: str
    api_key_env: str | None = None
    default_model: str | None = None
    timeout_seconds: int = 60
    headers: dict[str, str] = Field(default_factory=dict)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_home: str = "."
    timezone: str = "Asia/Shanghai"
    prompt_only: bool = True
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    default_provider: str | None = None
    default_model: str | None = None
    context_budget: str = "medium"
    ui_host: str = "127.0.0.1"
    ui_port: int = 8765


def _bool_from_env(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def default_config(root: Path | str = ".") -> AppConfig:
    return AppConfig(project_home=str(Path(root).resolve()))


def config_file_path(root: Path | str = ".", config_path: Path | str | None = None) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    env_path = os.getenv("AI_LEARNING_OS_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(root).resolve() / "config.yaml"


def load_config(
    root: Path | str = ".",
    *,
    config_path: Path | str | None = None,
    overrides: dict[str, Any] | None = None,
) -> AppConfig:
    data = default_config(root).model_dump()
    path = config_file_path(root, config_path)
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file must contain a mapping: {path}")
        data = _deep_merge(data, loaded)

    env_overrides: dict[str, Any] = {}
    if os.getenv("AI_LEARNING_OS_HOME"):
        env_overrides["project_home"] = os.environ["AI_LEARNING_OS_HOME"]
    if os.getenv("AI_LEARNING_OS_TIMEZONE"):
        env_overrides["timezone"] = os.environ["AI_LEARNING_OS_TIMEZONE"]
    if os.getenv("AI_LEARNING_OS_PROMPT_ONLY"):
        env_overrides["prompt_only"] = _bool_from_env(os.environ["AI_LEARNING_OS_PROMPT_ONLY"])
    if os.getenv("AI_LEARNING_OS_DEFAULT_PROVIDER"):
        env_overrides["default_provider"] = os.environ["AI_LEARNING_OS_DEFAULT_PROVIDER"]
    if os.getenv("AI_LEARNING_OS_DEFAULT_MODEL"):
        env_overrides["default_model"] = os.environ["AI_LEARNING_OS_DEFAULT_MODEL"]
    if os.getenv("AI_LEARNING_OS_CONTEXT_BUDGET"):
        env_overrides["context_budget"] = os.environ["AI_LEARNING_OS_CONTEXT_BUDGET"]
    if os.getenv("AI_LEARNING_OS_UI_HOST"):
        env_overrides["ui_host"] = os.environ["AI_LEARNING_OS_UI_HOST"]
    if os.getenv("AI_LEARNING_OS_UI_PORT"):
        env_overrides["ui_port"] = int(os.environ["AI_LEARNING_OS_UI_PORT"])

    data = _deep_merge(data, env_overrides)
    if overrides:
        data = _deep_merge(data, overrides)
    return AppConfig.model_validate(data)


def provider_summaries(config: AppConfig) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for provider_id, provider in sorted(config.providers.items()):
        key_present = bool(provider.api_key_env and os.getenv(provider.api_key_env))
        summaries.append(
            {
                "id": provider_id,
                "type": provider.type,
                "base_url": provider.base_url,
                "api_key_env": provider.api_key_env,
                "api_key_present": key_present,
                "default_model": provider.default_model,
                "is_default": provider_id == config.default_provider,
            }
        )
    return summaries


def public_config_summary(config: AppConfig) -> dict[str, Any]:
    return {
        "project_home": config.project_home,
        "timezone": config.timezone,
        "prompt_only": config.prompt_only,
        "default_provider": config.default_provider,
        "default_model": config.default_model,
        "context_budget": config.context_budget,
        "ui_host": config.ui_host,
        "ui_port": config.ui_port,
        "providers": provider_summaries(config),
    }
