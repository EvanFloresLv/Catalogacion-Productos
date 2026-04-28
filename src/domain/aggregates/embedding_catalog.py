from __future__ import annotations
from typing import Dict, List, Optional

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.embedding import Embedding
from domain.events.embedding_events import EmbeddingGeneratedEvent


class EmbeddingCatalog(AggregateRoot):
    """
    Aggregate root that manages a collection of embeddings.

    Invariants:
      - Each embedding must have a unique ID
      - Embeddings are immutable once created

    Events emitted:
      - EmbeddingGeneratedEvent
    """

    def __init__(self) -> None:
        super().__init__()
        self._embeddings: Dict[str, Embedding] = {}

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def embeddings(self) -> List[Embedding]:
        return list(self._embeddings.values())

    # ---------------------------
    # Commands
    # ---------------------------
    def add_embedding(self, embedding: Embedding) -> None:

        if embedding.id in self._embeddings:
            raise ValueError(f"Embedding with ID {embedding.id} already exists.")

        self._embeddings[embedding.id] = embedding

        self._record_event(EmbeddingGeneratedEvent(
            category_id=embedding.category_id,
            dimension=embedding.dimension,
            content_hash=embedding.content_hash,
        ))

    def add_embeddings_batch(self, embeddings: List[Embedding]) -> None:

        for embedding in embeddings:
            self._embeddings[embedding.id] = embedding

            self._record_event(EmbeddingGeneratedEvent(
                category_id=embedding.category_id,
                dimension=embedding.dimension,
                content_hash=embedding.content_hash,
            ))

    # ---------------------------
    # Queries on the aggregate
    # ---------------------------
    def get_embedding(self, embedding_id: str) -> Optional[Embedding]:
        return self._embeddings.get(embedding_id)

    def get_all_embeddings(self) -> List[Embedding]:
        return list(self._embeddings.values())