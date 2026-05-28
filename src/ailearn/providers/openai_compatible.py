from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..config import ProviderConfig
from ..ids import now_utc
from .base import ChatRequest, ChatResult, ProviderError


class OpenAICompatibleProvider:
    def __init__(self, provider_id: str, config: ProviderConfig):
        self.provider_id = provider_id
        self.config = config

    def _api_key(self) -> str | None:
        if not self.config.api_key_env:
            return None
        value = os.getenv(self.config.api_key_env)
        if not value:
            raise ProviderError(f"Missing API key env var: {self.config.api_key_env}")
        return value

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.config.headers}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _url(self, suffix: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{suffix.lstrip('/')}"

    def list_models(self) -> list[str]:
        request = urllib.request.Request(self._url("models"), headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"Provider model list failed: {exc}") from exc
        models = data.get("data", []) if isinstance(data, dict) else []
        return [str(item.get("id")) for item in models if isinstance(item, dict) and item.get("id")]

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._api_key()
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
        payload: dict[str, object] = {"model": model, "messages": messages}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        http_request = urllib.request.Request(
            self._url("chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"Provider chat request failed: {exc}") from exc
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if not choices:
            raise ProviderError("Provider response did not contain choices.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        text = str(message.get("content", ""))
        if not text:
            raise ProviderError("Provider response text was empty.")
        return ChatResult(
            text=text,
            provider=self.provider_id,
            model=str(data.get("model") or model),
            created_at=now_utc().isoformat(),
            raw_metadata={"id": data.get("id"), "object": data.get("object")},
            token_usage=data.get("usage") if isinstance(data.get("usage"), dict) else None,
        )
