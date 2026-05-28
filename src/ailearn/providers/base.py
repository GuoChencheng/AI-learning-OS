from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatRequest:
    user_prompt: str
    system_prompt: str | None = None
    context: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatResult:
    text: str
    provider: str
    model: str
    created_at: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    token_usage: dict[str, Any] | None = None


class ChatProvider(Protocol):
    provider_id: str

    def list_models(self) -> list[str]:
        ...

    def test_connection(self) -> tuple[bool, str]:
        ...

    def run_chat(self, request: ChatRequest) -> ChatResult:
        ...
