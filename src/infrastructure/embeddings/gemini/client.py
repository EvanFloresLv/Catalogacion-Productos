# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import time
import hashlib
from typing import List, Sequence

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import httpx
from google import genai

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import gemini_settings
from utils.circuit_breaker import CircuitBreaker
from application.ports.embedding_service import EmbeddingService
from infrastructure.embeddings.errors import (
    TransientEmbeddingError,
    PermanentEmbeddingError,
)
from utils.retry import sync_exponential_backoff_retry_sync


# ================================================================
# Embedding Client (SYNC)
# ================================================================

class EmbeddingClientHTTP(EmbeddingService):

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        retry_attempts: int = 3,
        embedding_dim: int = 768,
        enable_fallback: bool = False,
    ):
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.embedding_dim = embedding_dim
        self.enable_fallback = enable_fallback

        self.circuit_breaker = CircuitBreaker()

        self._client = genai.Client(
            vertexai=True,
            credentials=gemini_settings.google.credentials,
            project=gemini_settings.google.project_id,
            location=gemini_settings.location,
        )

    # ============================================================
    # Fallback Embedding
    # ============================================================

    def _fallback_embedding(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = [((b % 128) - 64) / 64.0 for b in digest]
        expanded = (base * ((self.embedding_dim // len(base)) + 1))[: self.embedding_dim]
        return [float(x) for x in expanded]

    # ============================================================
    # Core API Call (SYNC)
    # ============================================================

    def _embed_batch(self, texts: Sequence[str]) -> List[List[float]]:

        if self.circuit_breaker.is_open():
            raise PermanentEmbeddingError("Circuit breaker open")

        if not texts:
            raise ValueError("texts must not be empty")

        def do_request():
            try:
                response = self._client.models.embed_content(
                    model=gemini_settings.llm.embedding_model,
                    contents=list(texts),
                )

                embeddings = getattr(response, "embeddings", None)
                if not embeddings:
                    raise TransientEmbeddingError("No embeddings returned")

                normalized: List[List[float]] = []

                for e in embeddings:
                    values = getattr(e, "values", None) or getattr(e, "embedding", None)

                    if values is None:
                        raise TransientEmbeddingError(
                            "Embedding vector missing values"
                        )

                    vector = list(values)

                    if len(vector) != self.embedding_dim:
                        raise PermanentEmbeddingError(
                            f"Unexpected embedding dimension: {len(vector)} "
                            f"(expected {self.embedding_dim})"
                        )

                    normalized.append(vector)

                return normalized

            except httpx.ReadTimeout as e:
                raise TransientEmbeddingError(str(e)) from e

            except httpx.NetworkError as e:
                raise TransientEmbeddingError(str(e)) from e

            except TransientEmbeddingError:
                raise

            except Exception as e:
                raise PermanentEmbeddingError(str(e)) from e

        return sync_exponential_backoff_retry_sync(
            do_request,
            attempts=self.retry_attempts,
            base_delay=0.3,
            max_delay=3.0,
            retry_on=(TransientEmbeddingError,),
        )

    # ============================================================
    # Public API
    # ============================================================

    def generate(self, text: str) -> List[float]:

        if self.enable_fallback:
            return self._fallback_embedding(text)

        start = time.monotonic()

        try:
            result = self._embed_batch([text])
            self.circuit_breaker.record_success()
            return result[0]

        except Exception:
            self.circuit_breaker.record_failure()
            raise

        finally:
            latency = time.monotonic() - start
            # optionally log latency here


    def generate_batch(self, texts: Sequence[str]) -> List[List[float]]:

        if self.enable_fallback:
            return [self._fallback_embedding(t) for t in texts]

        start = time.monotonic()

        try:
            result = self._embed_batch(texts)
            self.circuit_breaker.record_success()
            return result

        except Exception:
            self.circuit_breaker.record_failure()
            raise

        finally:
            latency = time.monotonic() - start
            # optionally log latency here


    def close(self) -> None:
        if hasattr(self._client, "close"):
            self._client.close()
