from __future__ import annotations
from typing import List, Dict, Optional

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.brand import Brand
from domain.events.brand_events import (
    BrandCreatedEvent,
    BrandUpdatedEvent,
)


class BrandCatalog(AggregateRoot):
    """
    Aggregate root for managing a catalog of brands.

    Invariants:
        - Each brand must have a unique name
        - Brands can be updated but not deleted (soft delete)

    Events emitted:
        - BrandCreatedEvent
        - BrandUpdatedEvent
        - BrandDeletedEvent
    """
    def __init__(self):
        super().__init__()
        self._brands: Dict[str, Brand] = {}

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def brands(self) -> List[Brand]:
        return list(self._brands.values())

    # ---------------------------
    # Commands
    # ---------------------------
    def add_brand(self, brand: Brand):
        if brand.name in self._brands:
            raise ValueError("Brand with this name already exists.")
        self._brands[brand.name] = brand

        self._record_event(BrandCreatedEvent(
            name=brand.name,
            business=brand.business
        ))


    def add_brands_batch(self, brands: List[Brand]):

        for brand in brands:
            if brand.name in self._brands:
                raise ValueError(f"Brand with name {brand.name} already exists.")

            self._brands[brand.name] = brand

            self._record_event(BrandCreatedEvent(
                name=brand.name,
                business=brand.business
            ))

        return self._brands

    def update_brand(self, name: str, business: Optional[List[str]] = None):
        brand = self._brands.get(name)
        if not brand:
            raise ValueError("Brand not found.")

        if business is not None:
            brand.business = business

        self._record_event(BrandUpdatedEvent(
            name=brand.name,
            business=brand.business
        ))

    # ---------------------------
    # Queries on the aggregate
    # ---------------------------
    def get_brand(self, name: str) -> Optional[Brand]:
        return self._brands.get(name)

    def get_all_brands(self) -> List[Brand]:
        return self.brands