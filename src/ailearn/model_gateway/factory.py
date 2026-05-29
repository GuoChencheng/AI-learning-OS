from __future__ import annotations

import os

from .base import ModelGateway
from .fake import FakeModelGateway
from .openai_compatible import OpenAICompatibleGateway


def create_model_gateway_from_env() -> ModelGateway:
    """Return the configured real gateway, or FakeModelGateway when no provider is configured."""
    if os.getenv("OPENAI_API_KEY"):
        return OpenAICompatibleGateway()
    return FakeModelGateway()
