from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ModelGateway, ModelGatewayError, ModelTier


class OpenAICompatibleGateway(ModelGateway):
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.models = {
            ModelTier.FAST: os.getenv("AI_LEARN_FAST_MODEL", "gpt-4.1-mini"),
            ModelTier.MEDIUM: os.getenv("AI_LEARN_MEDIUM_MODEL", "gpt-4.1"),
            ModelTier.STRONG: os.getenv("AI_LEARN_STRONG_MODEL", "gpt-4.1"),
        }

    def complete(self, prompt: str, tier: ModelTier = ModelTier.FAST) -> str:
        if not self.api_key:
            raise ModelGatewayError("OPENAI_API_KEY is not configured.")
        payload = {
            "model": self.models[tier],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ModelGatewayError(str(exc)) from exc
        return data["choices"][0]["message"]["content"]

