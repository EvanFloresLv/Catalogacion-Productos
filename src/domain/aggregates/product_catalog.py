from __future__ import annotations
from typing import Dict, List, Optional

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.product import Product
from domain.events.product_events import ProductCreatedEvent


class ProductCatalog(AggregateRoot):
    """
    Aggregate root that manages a collection of products.

    Invariants:
      - Each product must have a unique ID
      - Products are immutable once created

    Events emitted:
      - ProductCreatedEvent
    """

    def __init__(self) -> None:
        super().__init__()
        self._products: Dict[str, Product] = {}

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def products(self) -> List[Product]:
        return list(self._products.values())

    # ---------------------------
    # Commands
    # ---------------------------
    def add_product(self, product: Product) -> None:

        if product.sku in self._products:
            raise ValueError(f"Product with SKU {product.sku} already exists.")

        self._products[product.sku] = product

        self._record_event(ProductCreatedEvent(
            sku=product.sku,
            name=product.name,
            description=product.description,
            product_type=product.product_type,
        ))

    def add_products_batch(self, products: List[Product]) -> None:

        for product in products:
            self._products[product.sku] = product

            self._record_event(ProductCreatedEvent(
                sku=product.sku,
                name=product.name,
                description=product.description,
                product_type=product.product_type,
            ))

    # ---------------------------
    # Queries on the aggregate
    # ---------------------------
    def get_product(self, sku: str) -> Optional[Product]:
        return self._products.get(sku)

    def get_all_products(self) -> List[Product]:
        return list(self._products.values())