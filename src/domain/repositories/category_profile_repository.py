# -----------------------------------------------------------------
# Domain Repository Interface — Category Profile
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Iterable, Optional

from domain.entities.category_profile import CategoryProfile


class CategoryProfileRepository(ABC):
    """Write-side repository for CategoryProfile."""

    @abstractmethod
    def save(self, profile: CategoryProfile) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, profiles: Iterable[CategoryProfile]) -> List[CategoryProfile]:
        raise NotImplementedError

    @abstractmethod
    def get_profiles_by_constraints(
        self,
        gender: Optional[str] = None,
        direction: Optional[str] = None,
        brand: Optional[str] = None,
        business: Optional[str] = None,
        is_leaf: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[CategoryProfile]:
        raise NotImplementedError

    @abstractmethod
    def list_all_profiles(self) -> List[CategoryProfile]:
        raise NotImplementedError
