# -----------------------------------------------------------------
# Schemas — Categories
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel, Field


# -----------------------------------------------------------------
# Requests
# -----------------------------------------------------------------
class LoadCategoriesRequest(BaseModel):
    business: str = Field(..., min_length=1, examples=["liverpool"])
    brand: str | None = Field(default=None, examples=["nike"])


class GetCategoryTreeRequest(BaseModel):
    root_category_id: str | None = None


class GetCategoriesByConstraintsRequest(BaseModel):
    gender: str | None = None
    direction: str | None = None
    business: str | None = None
    brand: str | None = None
    is_leaf: bool | None = None
    limit: int | None = Field(default=None, ge=1, le=500)


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class CategoryResponse(BaseModel):
    id: str
    name: str
    level: int
    parent_id: str | None = None
    is_leaf: bool | None = None
    gender: str | None = None
    direction: str | None = None
    brand: str | None = None
    business: str | None = None
    keywords: list[str] = []


class LoadCategoriesResponse(BaseModel):
    categories_count: int
    embeddings_count: int


class CategoryTreeNodeResponse(BaseModel):
    id: str
    name: str
    level: int
    keyword_count: int
    children: list[CategoryTreeNodeResponse] = []
