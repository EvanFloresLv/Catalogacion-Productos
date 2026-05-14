# -----------------------------------------------------------------
# Controller — Classification Endpoints
# -----------------------------------------------------------------
from __future__ import annotations
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from infrastructure.web.dependencies import (
    get_session,
    get_classify_product_use_case,
    get_classify_batch_use_case,
)
from infrastructure.persistence.postgresql.repositories.product_repository_pg import ProductRepositoryPG
from infrastructure.web.schemas.classification_schemas import (
    ClassifyProductRequest,
    ClassifyBatchProductsRequest,
    ClassifyProductResponse,
    BatchClassificationResponse,
    ClassificationResultResponse,
    CategoryMatchResponse,
    QueryConstraintsResponse,
)
from application.use_cases.classification.classify_product import ClassifyProductCommand
from application.use_cases.classification.classify_batch_products import ClassifyBatchProductsCommand

router = APIRouter(prefix="/classification", tags=["Classification"])


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------
def _to_match_response(match) -> CategoryMatchResponse:
    return CategoryMatchResponse(
        category_id=match.category_id,
        score=match.score,
        path=match.path,
    )


def _to_query_response(query_str: str | None) -> QueryConstraintsResponse | None:
    if not query_str:
        return None

    def _extract(field: str) -> str | None:
        m = re.search(rf"{field}='?([^',)]+)'?", query_str)
        return m.group(1) if m and m.group(1) != "None" else None

    def _extract_list(field: str) -> list[str] | None:
        m = re.search(rf"{field}=\[([^\]]*)\]", query_str)
        if not m:
            return None
        items = [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()]
        return items if items else None

    return QueryConstraintsResponse(
        article_group=_extract_list("article_group"),
        gender=_extract("gender"),
        direction=_extract("direction"),
        business=_extract("business"),
        brand=_extract("brand"),
        is_leaf=_extract("is_leaf") == "True" if _extract("is_leaf") else None,
        limit=int(_extract("limit")) if _extract("limit") else None,
    )


def _to_result_response(result, product_name: str = "") -> dict | None:
    if result is None:
        return None
    return {
        "product_sku": result.product_sku,
        "product_name": product_name,
        "best": {
            "category_id": result.best.category_id,
            "score": result.best.score,
            "path": result.best.path,
        },
        "top_k": [
            {
                "category_id": m.category_id,
                "score": m.score,
                "path": m.path,
            }
            for m in result.top_k
        ],
        "query": _to_query_response(result.query),
    }


# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/product", response_model=ClassifyProductResponse)
def classify_product(
    body: ClassifyProductRequest,
    session: Session = Depends(get_session),
):
    use_case = get_classify_product_use_case(session)
    cmd = ClassifyProductCommand(product_sku=body.product_sku, top_k=body.top_k)
    results = use_case.execute(cmd)

    if not results:
        raise HTTPException(status_code=404, detail=f"No results for SKU {body.product_sku}")

    product = ProductRepositoryPG(session).get_by_sku(body.product_sku)
    product_name = product.name if product else ""

    return ClassifyProductResponse(
        results={
            business: _to_result_response(result, product_name)
            for business, result in results.items()
        }
    )


@router.post("/batch", response_model=BatchClassificationResponse)
def classify_batch(
    body: ClassifyBatchProductsRequest,
    session: Session = Depends(get_session),
):
    use_case = get_classify_batch_use_case(session)
    cmd = ClassifyBatchProductsCommand(
        product_skus=tuple(body.product_skus),
        top_k=body.top_k,
    )
    batch = use_case.execute(cmd)

    # Fetch product names for all SKUs
    product_repo = ProductRepositoryPG(session)
    products = product_repo.get_by_skus(list(body.product_skus))
    name_map = {p.sku: p.name for p in products}

    return BatchClassificationResponse(
        results={
            sku: {
                biz: _to_result_response(res, name_map.get(sku, ""))
                for biz, res in biz_results.items()
            }
            for sku, biz_results in batch.results.items()
        },
        failed=batch.failed,
        succeeded_count=batch.succeeded_count,
        failed_count=batch.failed_count,
        total=batch.total,
    )
