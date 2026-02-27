# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.embeddings.embedding import Embedding


class EmbeddingRepository(ABC):

    @abstractmethod
    def save(
        self, embedding: Embedding
    ) -> None:
        raise NotImplementedError


    @abstractmethod
    def save_batch(
        self, embeddings: list[Embedding]
    ) -> None:
        raise NotImplementedError


    @abstractmethod
    def get_by_category_id(
        self, category_id: UUID
    ) -> Optional[Embedding]:
        raise NotImplementedError


    @abstractmethod
    def get_by_category_ids(
        self, category_ids: list[UUID]
    ) -> list[Embedding]:
        raise NotImplementedError


    @abstractmethod
    def search_similar(
        self, query_vector: list[float], limit: int
    ) -> list[Embedding]:
        raise NotImplementedError