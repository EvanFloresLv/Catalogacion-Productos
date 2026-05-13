# Lazy imports — avoid eager model registration that causes
# "Table already defined" errors when models/__init__.py also imports them.

from .llm.gemini.client import LLMClient
from .embeddings.gemini.client import EmbeddingClient

__all__ = [
    "CategoryRepositoryPG",
    "EmbeddingRepositoryPG",
    "ProductRepositoryPG",
    "CategoryModel",
    "EmbeddingModel",
    "ProductModel",
    "OutboxModel",
    "SqlAlchemyUnitOfWork",
    "LLMClient",
    "EmbeddingClient",
]