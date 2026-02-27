# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import hashlib

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import numpy as np

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.embedding_service import EmbeddingService


class FakeEmbeddingService(EmbeddingService):

    def __init__(self, dim: int = 64):
        self._dim = dim


    def dimension(self):
        return self._dim


    def embed_text(self, text: str) -> list[float]:

        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "big")

        rng = np.random.default_rng(seed)
        v = rng.normal(size=(self._dim,)).astype("float32")

        # Normalizar para cosine similarity
        v /= np.linalg.norm(v) + 1e-12
        return v.tolist()