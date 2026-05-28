from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import ProviderConfig
from ..ids import now_utc
from .base import ChatRequest, ChatResult, ProviderError


class OllamaProvider:
    def __init__(self, provider_id: str, config: ProviderConfig):
        self.provider_id = provider_id
        self.config = config

    def _url(self, suffix: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{suffix.lstrip('/')}"

    def list_models(self) -> list[str]:
        request = urllib.request.Request(self._url("api/tags"), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"Ollama model list failed: {exc}") from exc
        models = data.get("models", []) if isinstance(data, dict) else []
        return [str(item.get("name")) for item in models if isinstance(item, dict) and item.get("name")]

    def test_connection(self) -> tuple[bool, str]:
        try:
            models = self.list_models()
        except ProviderError as exc:
            return False, str(exc)
        return True, f"Connected to {self.provider_id}; {len(models)} model(s) visible."

    def run_chat(self, request: ChatRequest) -> ChatResult:
        model = request.model or self.config.default_model
        if not model:
            raise ProviderError(f"No model configured for provider: {self.provider_id}")
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        user_content = request.user_prompt
        if request.context:
            user_content = f"Context selected by ai-learning-os:\n\n{request.context}\n\nUser prompt:\n\n{request.user_prompt}"
        messages.append({"role": "user", "content": user_content})
        payload = {"model": model, "messages": messages, "stream": False}
        http_request = urllib.request.Request(
            self._url("api/chat"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **self.config.headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"Ollama chat request failed: {exc}") from exc
        message = data.get("message", {}) if isinstance(data, dict) else {}
        text = str(message.get("content", ""))
        if not text:
            raise ProviderError("Ollama response text was empty.")
        return ChatResult(
            text=text,
            provider=self.provider_id,
            model=str(data.get("model") or model),
            created_at=now_utc().isoformat(),
            raw_metadata={"done": data.get("done")},
            token_usage=None,
        )
