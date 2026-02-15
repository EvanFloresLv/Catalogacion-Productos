# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.embedding_service import EmbeddingService


class SentenceTransformersEmbeddingService(EmbeddingService):

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError("Please install the 'sentence-transformers' package.")


    def embed_text(self, text: str) -> list[float]:
        vector = self.model.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in vector]