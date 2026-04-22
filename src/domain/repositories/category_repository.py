# -----------------------------------------------------------------
# Domain Repository Interface — Category
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.category import Category


class CategoryRepository(ABC):
    """Write-side repository for Category aggregate."""

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
