from __future__ import annotations

import os
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_FAST_MODEL = "deepseek-v4-flash"
DEFAULT_MEDIUM_MODEL = "deepseek-v4-flash"
DEFAULT_STRONG_MODEL = "deepseek-v4-pro"
LOCAL_PROVIDER_FILENAME = ".env.local"


def local_provider_path(root: Path | str | None = None) -> Path:
    configured = os.getenv("AI_LEARN_LOCAL_PROVIDER_FILE")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(root or ".").resolve() / LOCAL_PROVIDER_FILENAME)


def load_local_provider_values(root: Path | str | None = None) -> dict[str, str]:
    path = local_provider_path(root)
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = _unquote_env_value(value.strip())
    return values


def effective_local_provider_values(root: Path | str | None = None) -> dict[str, str]:
    stored = load_local_provider_values(root)
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or stored.get("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL") or stored.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
        "AI_LEARN_FAST_MODEL": os.getenv("AI_LEARN_FAST_MODEL") or stored.get("AI_LEARN_FAST_MODEL", DEFAULT_FAST_MODEL),
        "AI_LEARN_MEDIUM_MODEL": os.getenv("AI_LEARN_MEDIUM_MODEL") or stored.get("AI_LEARN_MEDIUM_MODEL", DEFAULT_MEDIUM_MODEL),
        "AI_LEARN_STRONG_MODEL": os.getenv("AI_LEARN_STRONG_MODEL") or stored.get("AI_LEARN_STRONG_MODEL", DEFAULT_STRONG_MODEL),
    }


def public_local_provider_settings(root: Path | str | None = None) -> dict[str, Any]:
    values = effective_local_provider_values(root)
    path = local_provider_path(root)
    return {
        "provider_id": "deepseek",
        "type": "openai_compatible",
        "base_url": values["OPENAI_BASE_URL"],
        "fast_model": values["AI_LEARN_FAST_MODEL"],
        "medium_model": values["AI_LEARN_MEDIUM_MODEL"],
        "strong_model": values["AI_LEARN_STRONG_MODEL"],
        "api_key_present": bool(values["OPENAI_API_KEY"]),
        "storage_path": str(path),
        "storage_file": path.name,
        "local_storage_ignored": path.name in {".env.local", ".env"} or path.name.startswith(".env."),
    }


def save_local_provider_settings(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    fast_model: str | None = None,
    medium_model: str | None = None,
    strong_model: str | None = None,
    root: Path | str | None = None,
) -> dict[str, Any]:
    existing = effective_local_provider_values(root)
    values = {
        "OPENAI_API_KEY": _clean(api_key) if api_key is not None and api_key.strip() else existing["OPENAI_API_KEY"],
        "OPENAI_BASE_URL": _clean(base_url) or existing["OPENAI_BASE_URL"] or DEFAULT_BASE_URL,
        "AI_LEARN_FAST_MODEL": _clean(fast_model) or existing["AI_LEARN_FAST_MODEL"] or DEFAULT_FAST_MODEL,
        "AI_LEARN_MEDIUM_MODEL": _clean(medium_model) or existing["AI_LEARN_MEDIUM_MODEL"] or DEFAULT_MEDIUM_MODEL,
        "AI_LEARN_STRONG_MODEL": _clean(strong_model) or existing["AI_LEARN_STRONG_MODEL"] or DEFAULT_STRONG_MODEL,
    }
    path = local_provider_path(root)
    path.write_text(_format_env(values), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ.update(values)
    return public_local_provider_settings(root)


def _format_env(values: dict[str, str]) -> str:
    lines = [
        "# AI Learn OS local provider settings.",
        "# This file is intentionally ignored by git. Do not commit real API keys.",
    ]
    for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "AI_LEARN_FAST_MODEL", "AI_LEARN_MEDIUM_MODEL", "AI_LEARN_STRONG_MODEL"]:
        lines.append(f"{key}={_quote_env_value(values[key])}")
    return "\n".join(lines) + "\n"


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _quote_env_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("Provider settings cannot contain newlines.")
    return value


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
