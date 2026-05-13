# -----------------------------------------------------------------
# Schemas — Brands
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class BrandResponse(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    id: str
    name: str
    business: list[str]

    @classmethod
    def from_entity(cls, b) -> "BrandResponse":
        return cls(id=str(b.id), name=b.name, business=list(b.business))


class LoadBrandsResponse(BaseModel):
    brands_count: int
