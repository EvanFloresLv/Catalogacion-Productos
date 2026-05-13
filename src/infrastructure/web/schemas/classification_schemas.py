# -----------------------------------------------------------------
# Schemas — Classification
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel, Field


# -----------------------------------------------------------------
# Requests
# -----------------------------------------------------------------
class ClassifyProductRequest(BaseModel):
    product_sku: str = Field(..., min_length=1, examples=["1192296534"])
    top_k: int = Field(default=5, ge=1, le=20)


class ClassifyBatchProductsRequest(BaseModel):
    product_skus: list[str] = Field(..., min_length=1, examples=[["1192296534", "1196142564"]])
    top_k: int = Field(default=5, ge=1, le=20)


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class CategoryMatchResponse(BaseModel):
    category_id: str
    score: float
    path: str | None = None


class QueryConstraintsResponse(BaseModel):
    article_group: list[str] | None = None
    gender: str | None = None
    direction: str | None = None
    business: str | None = None
    brand: str | None = None
    is_leaf: bool | None = None
    limit: int | None = None


class ClassificationResultResponse(BaseModel):
    product_sku: str
    product_name: str
    best: CategoryMatchResponse
    top_k: list[CategoryMatchResponse]
    query: QueryConstraintsResponse | None = None


class ClassifyProductResponse(BaseModel):
    results: dict[str, ClassificationResultResponse | None]


class BatchClassificationResponse(BaseModel):
    results: dict[str, dict[str, ClassificationResultResponse | None]]
    failed: dict[str, str]
    succeeded_count: int
    failed_count: int
    total: int
