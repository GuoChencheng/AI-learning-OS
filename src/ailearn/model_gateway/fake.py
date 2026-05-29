from __future__ import annotations

import json
from typing import Any

from .base import ModelGateway, ModelTier


class FakeModelGateway(ModelGateway):
    """Deterministic gateway used by tests and local development."""

    def __init__(self, responses: list[str | dict[str, Any]] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def complete(self, prompt: str, tier: ModelTier = ModelTier.FAST) -> str:
        self.calls.append({"prompt": prompt, "tier": tier.value})
        if self.responses:
            value = self.responses.pop(0)
            return json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
        return json.dumps({"answer": "fake response"}, ensure_ascii=False)

