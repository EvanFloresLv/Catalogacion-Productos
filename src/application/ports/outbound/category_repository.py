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
from domain.categories.category import Category


class CategoryRepository(ABC):

    @abstractmethod
    def save(
        self,
        category: Category
    ) -> None:
        """Saves a category to the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_all(self) -> list[Category]:
        """Retrieves all categories from the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_by_id(
        self,
        category_id: UUID
    ) -> Category | None:
        """Retrieves a category by its ID from the repository."""
        raise NotImplementedError