# -----------------------------------------------------------------
# Application DTO — Commands — Classification
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassifyProductCommand:
    """Command to classify a product into categories."""
    product_sku: str
    top_k: int = 5
