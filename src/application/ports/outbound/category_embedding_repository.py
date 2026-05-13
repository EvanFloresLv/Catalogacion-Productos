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


class CategoryEmbeddingRepository(ABC):

    @abstractmethod
    def upsert(
        self,
        category: UUID,
        vector: list[float]
    ) -> None:
        """Upserts a category vector into the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_all(self) -> list[tuple[UUID, list[float]]]:
        """Retrieves all category vectors from the repository."""
        raise NotImplementedError


    @abstractmethod
    def delete_all(self) -> None:
        """Deletes all category vectors from the repository."""
        raise NotImplementedError