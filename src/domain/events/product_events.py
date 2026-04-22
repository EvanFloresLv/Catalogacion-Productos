# -----------------------------------------------------------------
# Domain Events — Product
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class ProductCreatedEvent(DomainEvent):
    """Emitted when a new product is created."""
    sku: str = ""
    name: str = ""
    product_type: str = ""
    business: List[str] | None = None


@dataclass(frozen=True)
class ProductClassifiedEvent(DomainEvent):
    """Emitted when a product is successfully classified."""
    sku: str = ""
    business: str = ""
    best_category_id: str = ""
    best_score: float = 0.0
    top_k_count: int = 0
