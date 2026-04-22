# -----------------------------------------------------------------
# Domain Repository Interface — Product
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.product import Product


class ProductRepository(ABC):
    """Write-side repository for Product aggregate."""

    @abstractmethod
    def save(self, product: Product) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_batch(self, products: List[Product]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[Product]:
        raise NotImplementedError

    @abstractmethod
    def get_by_skus(self, skus: List[str]) -> List[Product]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[Product]:
        raise NotImplementedError
