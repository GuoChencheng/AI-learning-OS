from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


class ModelTier(StrEnum):
    FAST = "fast"
    MEDIUM = "medium"
    STRONG = "strong"


T = TypeVar("T", bound=BaseModel)


class ModelGatewayError(RuntimeError):
    pass


class ModelGateway:
    def complete(self, prompt: str, tier: ModelTier = ModelTier.FAST) -> str:
        raise NotImplementedError

    def complete_structured(self, prompt: str, schema: type[T], tier: ModelTier = ModelTier.FAST, fallback: T | None = None) -> T:
        raw = self.complete(prompt, tier=tier)
        for candidate in (raw, _extract_json_object(raw)):
            if candidate is None:
                continue
            try:
                return schema.model_validate(json.loads(candidate))
            except (json.JSONDecodeError, ValidationError):
                continue
        if fallback is not None:
            return fallback
        raise ModelGatewayError(f"Model output did not validate as {schema.__name__}")


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]

