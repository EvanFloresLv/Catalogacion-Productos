# -----------------------------------------------------------------
# Controller — Classification Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from infrastructure.web.dependencies import (
    get_session,
    get_classify_product_use_case,
    get_classify_batch_use_case,
)
from infrastructure.web.schemas.classification_schemas import (
    ClassifyProductRequest,
    ClassifyBatchProductsRequest,
    ClassifyProductResponse,
    BatchClassificationResponse,
    ClassificationResultResponse,
    CategoryMatchResponse,
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


def _to_result_response(result) -> ClassificationResultResponse | None:
    if result is None:
        return None
    return ClassificationResultResponse(
        product_sku=result.product_sku,
        best=_to_match_response(result.best),
        top_k=[_to_match_response(m) for m in result.top_k],
    )


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

    return ClassifyProductResponse(
        results={
            business: _to_result_response(result)
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

    return BatchClassificationResponse(
        results={
            sku: {
                biz: _to_result_response(res)
                for biz, res in biz_results.items()
            }
            for sku, biz_results in batch.results.items()
        },
        failed=batch.failed,
        succeeded_count=batch.succeeded_count,
        failed_count=batch.failed_count,
        total=batch.total,
    )
