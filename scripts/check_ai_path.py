from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(SRC), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ailearn.model_gateway.base import ModelTier
from ailearn.model_gateway.factory import create_model_gateway_from_env
from ailearn.settings.local_provider import public_local_provider_settings


def describe_ai_path() -> dict[str, Any]:
    gateway = create_model_gateway_from_env()
    models = getattr(gateway, "models", {}) or {}
    local_provider = public_local_provider_settings()
    return {
        "gateway_selected": gateway.__class__.__name__,
        "fast_model": _model_name(models, ModelTier.FAST, local_provider["fast_model"]),
        "medium_model": _model_name(models, ModelTier.MEDIUM, local_provider["medium_model"]),
        "strong_model": _model_name(models, ModelTier.STRONG, local_provider["strong_model"]),
        "openai_base_url": local_provider["base_url"],
        "openai_api_key_configured": "yes" if local_provider["api_key_present"] else "no",
        "local_provider_file": local_provider["storage_file"],
    }


def _model_name(models: dict[Any, Any], tier: ModelTier, default: str) -> str:
    configured = models.get(tier)
    return str(configured or default)


def main() -> None:
    print(json.dumps(describe_ai_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
