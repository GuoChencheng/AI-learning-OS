from __future__ import annotations

from ..config import AppConfig, provider_summaries
from .base import ChatProvider, ProviderError
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider


PROVIDER_TYPES = {
    "openai_compatible": OpenAICompatibleProvider,
    "ollama": OllamaProvider,
}


def build_provider(config: AppConfig, provider_id: str | None = None) -> ChatProvider:
    resolved_id = provider_id or config.default_provider
    if not resolved_id:
        raise ProviderError("No provider selected. Configure default_provider or pass --provider.")
    provider_config = config.providers.get(resolved_id)
    if provider_config is None:
        raise ProviderError(f"Provider is not configured: {resolved_id}")
    provider_cls = PROVIDER_TYPES.get(provider_config.type)
    if provider_cls is None:
        supported = ", ".join(sorted(PROVIDER_TYPES))
        raise ProviderError(f"Unsupported provider type: {provider_config.type}. Supported: {supported}")
    return provider_cls(resolved_id, provider_config)


def configured_provider_summaries(config: AppConfig) -> list[dict[str, object]]:
    return provider_summaries(config)
