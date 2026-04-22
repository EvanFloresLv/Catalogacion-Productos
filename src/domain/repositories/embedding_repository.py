# -----------------------------------------------------------------
# Domain Repository Interface — Embedding
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from domain.entities.embedding import Embedding


class EmbeddingRepository(ABC):
    """Write-side repository for Embedding entity."""

    @abstractmethod
    def save(self, embedding: Embedding) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, embeddings: List[Embedding]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_category_id(self, category_id: str) -> Optional[Embedding]:
        raise NotImplementedError

    @abstractmethod
    def get_by_category_ids(self, category_ids: List[str]) -> List[Embedding]:
        raise NotImplementedError

    @abstractmethod
    def find_by_hashes(self, hashes: List[str]) -> List[Embedding]:
        raise NotImplementedError

    @abstractmethod
    def search_similar(
        self,
        query_vector: List[float],
        category_ids: List[str],
        limit: int,
    ) -> List[Tuple[Embedding, float]]:
        raise NotImplementedError
