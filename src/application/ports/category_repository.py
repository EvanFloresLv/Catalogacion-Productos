# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.category import Category


class CategoryRepository(ABC):

    @abstractmethod
    def save(
        self,
        category: Category
    ) -> None:
        raise NotImplementedError


    @abstractmethod
    def save_batch(
        self,
        categories: list[Category]
    ) -> None:
        raise NotImplementedError


    @abstractmethod
    def get_all(self) -> list[Category]:
        raise NotImplementedError


    @abstractmethod
    def get_by_id(
        self,
        category_id: str
    ) -> Category | None:
        raise NotImplementedError