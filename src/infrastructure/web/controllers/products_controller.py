# -----------------------------------------------------------------
# Controller — Products Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

import tempfile
import shutil

from infrastructure.web.dependencies import (
    get_session,
    get_load_products_use_case,
)
from infrastructure.web.schemas.products_schemas import (
    ProductResponse,
    LoadProductsResponse,
)
from application.use_cases.products.load_products_from_file import (
    LoadProductsFromFileCommand,
)
from config.composition_root import create_product_repository

router = APIRouter(prefix="/products", tags=["Products"])


# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/load", response_model=LoadProductsResponse)
def load_products_from_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    use_case = get_load_products_use_case(session)
    cmd = LoadProductsFromFileCommand(file_path=tmp_path, enhance=True)
    result = use_case.execute(cmd)

    return LoadProductsResponse(
        products=[str(sku) for sku in result],
        products_count=len(result)
    )


@router.get("/{sku}", response_model=ProductResponse)
def get_product_by_sku(
    sku: str,
    session: Session = Depends(get_session),
):
    repo = create_product_repository(session)
    product = repo.get_by_sku(sku)

    if not product:
        raise HTTPException(status_code=404, detail=f"Product with SKU {sku} not found.")

    return ProductResponse(
        sku=product.sku,
        name=product.name,
        brand=product.brand,
        direction=product.direction,
        product_type=product.product_type,
        category=product.category,
        business=list(product.business),
        gender=product.gender,
        description=product.description,
        keywords=list(product.keywords) if product.keywords else [],
        article_group=list(product.article_group) if product.article_group else None,
    )
