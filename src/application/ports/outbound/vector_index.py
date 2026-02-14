# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class VectorIndex(ABC):

    @abstractmethod
    def reset(
        self,
        dim: int
    ) -> None:
        """Resets the vector index."""
        raise NotImplementedError


    @abstractmethod
    def upsert(
        self,
        item_id: UUID,
        vector: list[float]
    ) -> None:
        """Upserts a vector into the index."""
        raise NotImplementedError


    @abstractmethod
    def search(
        self,
        vector: list[float],
        top_k: int
    ) -> list[tuple[UUID, float]]:
        """Searches for the most similar vectors in the index."""
        raise NotImplementedError