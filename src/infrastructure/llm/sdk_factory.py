# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import threading
from typing import Iterable

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from llm_sdk.sync_sdk import LLM
from llm_sdk.providers.sync_registry import ProviderRegistry, ProviderSpec
from llm_sdk_provider_gemini import SyncGeminiClient

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import gemini_settings


_PROVIDER_NAME = gemini_settings.llm.provider
_LOCATION = gemini_settings.location
_MODELS: tuple[str, ...] = (
    gemini_settings.llm.model,
    gemini_settings.llm.model_fast,
    gemini_settings.llm.model_pro,
)

_lock = threading.Lock()
_sdk: LLM | None = None


def get_llm_sdk() -> LLM:
    global _sdk
    if _sdk is not None:
        return _sdk

    with _lock:
        if _sdk is None:
            sdk = LLM.default()
            _register_gemini(sdk.registry)
            _sdk = sdk
        return _sdk


def _register_gemini(registry: ProviderRegistry, *, models: Iterable[str] | None = None) -> None:
    name = _PROVIDER_NAME
    if name in registry.list_providers():
        return

    spec = ProviderSpec(
        name=name,
        factory=lambda: SyncGeminiClient(location=_LOCATION),
        models=set(models) if models is not None else set(_MODELS),
    )
    registry.register(spec)


def reset_for_tests() -> None:
    global _sdk
    with _lock:
        _sdk = None
