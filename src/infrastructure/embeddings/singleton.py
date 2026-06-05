from __future__ import annotations

import logging
import threading
from typing import Optional

from google import genai

from config.settings import gemini_settings
from infrastructure.embeddings.gemini.client import EmbeddingClient

logger = logging.getLogger(__name__)

_genai_client: Optional[genai.Client] = None
_embedding_client: Optional[EmbeddingClient] = None
_lock = threading.RLock()
_warmed_up: bool = False


def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    with _lock:
        if _genai_client is not None:
            return _genai_client

        _genai_client = genai.Client(
            vertexai=True,
            credentials=gemini_settings.google.credentials,
            project=gemini_settings.google.project_id,
            location=gemini_settings.location,
        )
        logger.info(
            "[EmbeddingSingleton] genai.Client initialized (project=%s, location=%s)",
            gemini_settings.google.project_id,
            gemini_settings.location,
        )
        return _genai_client


def get_embedding_client(embedding_dim: int = 768) -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is not None and _embedding_client.embedding_dim == embedding_dim:
        return _embedding_client

    with _lock:
        if _embedding_client is not None and _embedding_client.embedding_dim == embedding_dim:
            return _embedding_client

        _embedding_client = EmbeddingClient(
            client=get_genai_client(),
            embedding_dim=embedding_dim,
        )
        return _embedding_client


def warmup_clients(embedding_dim: int = 768) -> None:
    global _warmed_up
    if _warmed_up:
        return

    with _lock:
        if _warmed_up:
            return
        get_embedding_client(embedding_dim=embedding_dim)
        _warmed_up = True
        logger.info("[EmbeddingSingleton] clients warmed up")


def reset_for_tests() -> None:
    global _genai_client, _embedding_client, _warmed_up
    with _lock:
        _genai_client = None
        _embedding_client = None
        _warmed_up = False
