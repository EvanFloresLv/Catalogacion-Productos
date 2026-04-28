# -----------------------------------------------------------------
# Domain Repository Interface — Category
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.category import Category


class CategoryRepository(ABC):

    @abstractmethod
    def save(self, category: Category) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, categories: List[Category]) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, category_id: str) -> Optional[Category]:
        raise NotImplementedError

    @abstractmethod
    def get_by_ids(self, category_ids: List[str]) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    def get_profiles_by_constraints(
        self,
        gender: Optional[str] = None,
        direction: Optional[str] = None,
        brand: Optional[str] = None,
        is_leaf: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[Category]:
        raise NotImplementedError