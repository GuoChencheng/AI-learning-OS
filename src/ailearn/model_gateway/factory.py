from __future__ import annotations

from .base import ModelGateway
from .base import ModelTier
from .fake import FakeModelGateway
from .openai_compatible import OpenAICompatibleGateway
from ailearn.settings.local_provider import effective_local_provider_values


def create_model_gateway_from_env() -> ModelGateway:
    """Return the configured real gateway, or FakeModelGateway when no provider is configured."""
    values = effective_local_provider_values()
    if values["OPENAI_API_KEY"]:
        return OpenAICompatibleGateway(
            api_key=values["OPENAI_API_KEY"],
            base_url=values["OPENAI_BASE_URL"],
            models={
                ModelTier.FAST: values["AI_LEARN_FAST_MODEL"],
                ModelTier.MEDIUM: values["AI_LEARN_MEDIUM_MODEL"],
                ModelTier.STRONG: values["AI_LEARN_STRONG_MODEL"],
            },
        )
    return FakeModelGateway()
