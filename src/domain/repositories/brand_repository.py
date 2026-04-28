# -----------------------------------------------------------------
# Domain Repository Interface — Category
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.brand import Brand


class BrandRepository(ABC):

    @abstractmethod
    def save(self, brand: Brand) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, brands: List[Brand]) -> List[Brand]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[Brand]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, brand_id: str) -> Optional[Brand]:
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, brand_name: str) -> Optional[Brand]:
        raise NotImplementedError

    @abstractmethod
    def get_by_business(self, business_str: str) -> List[Brand]:
        raise NotImplementedError