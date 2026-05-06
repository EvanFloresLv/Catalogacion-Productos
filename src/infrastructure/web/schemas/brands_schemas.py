# -----------------------------------------------------------------
# Schemas — Brands
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class BrandResponse(BaseModel):
    id: str
    name: str
    business: list[str]


class LoadBrandsResponse(BaseModel):
    brands_count: int
