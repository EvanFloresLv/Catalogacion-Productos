# -----------------------------------------------------------------
# Application DTO — Queries — Product
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GetProductBySkuQuery:
    """Query to get a product by SKU."""
    sku: str


@dataclass(frozen=True)
class GetProductsBySkusQuery:
    """Query to get multiple products by SKUs."""
    skus: List[str]
