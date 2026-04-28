# -----------------------------------------------------------------
# Domain Events — Product
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class ProductCreatedEvent(DomainEvent):
    sku: str = ""
    name: str = ""
    description: str = ""
    product_type: str = ""


@dataclass(frozen=True)
class ProductClassifiedEvent(DomainEvent):
    sku: str = ""
    business: str = ""
    best_category_id: str = ""
    best_score: float = 0.0
    top_k_count: int = 0
