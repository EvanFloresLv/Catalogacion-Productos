# -----------------------------------------------------------------
# Schemas — Products
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class ProductResponse(BaseModel):
    sku: str
    name: str
    brand: str
    direction: str
    product_type: str
    business: list[str]
    gender: str | None = None
    description: str | None = None
    keywords: list[str] = []


class LoadProductsResponse(BaseModel):
    products: list[str]
    products_count: int
