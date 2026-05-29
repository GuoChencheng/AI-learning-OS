from __future__ import annotations

import json
import os
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


def describe_ai_path() -> dict[str, Any]:
    gateway = create_model_gateway_from_env()
    models = getattr(gateway, "models", {}) or {}
    return {
        "gateway_selected": gateway.__class__.__name__,
        "fast_model": _model_name(models, ModelTier.FAST, "AI_LEARN_FAST_MODEL", "gpt-4.1-mini"),
        "medium_model": _model_name(models, ModelTier.MEDIUM, "AI_LEARN_MEDIUM_MODEL", "gpt-4.1"),
        "strong_model": _model_name(models, ModelTier.STRONG, "AI_LEARN_STRONG_MODEL", "gpt-4.1"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "openai_api_key_configured": "yes" if os.getenv("OPENAI_API_KEY") else "no",
    }


def _model_name(models: dict[Any, Any], tier: ModelTier, env_name: str, default: str) -> str:
    configured = models.get(tier)
    return str(configured or os.getenv(env_name, default))


def main() -> None:
    print(json.dumps(describe_ai_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
