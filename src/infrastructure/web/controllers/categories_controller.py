# -----------------------------------------------------------------
# Controller — Categories Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

import tempfile
import shutil

from infrastructure.web.dependencies import (
    get_session,
    get_load_categories_use_case,
    get_category_query_service,
)
from infrastructure.web.schemas.categories_schemas import (
    LoadCategoriesResponse,
    CategoryResponse,
    CategoryTreeNodeResponse,
)
from application.use_cases.categories.load_categories_from_file import (
    LoadCategoriesFromFileCommand,
)
from application.dto.queries.category_queries import (
    GetCategoryTreeQuery,
    GetCategoriesByConstraintsQuery,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/load", response_model=LoadCategoriesResponse)
def load_categories_from_file(
    file: UploadFile = File(...),
    business: str = Form(...),
    brand: str | None = Form(default=None),
    session: Session = Depends(get_session),
):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    use_case = get_load_categories_use_case(session)
    cmd = LoadCategoriesFromFileCommand(
        file_path=tmp_path,
        business=business,
        brand=brand,
    )
    result = use_case.execute(cmd)

    return LoadCategoriesResponse(
        categories_count=len(result["categories"]),
        embeddings_count=len(result["embeddings"]),
    )


@router.get("/tree", response_model=list[CategoryTreeNodeResponse])
def get_category_tree(
    root_category_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    service = get_category_query_service(session)
    query = GetCategoryTreeQuery(root_category_id=root_category_id)
    return service.get_category_tree(query)


@router.get("/search", response_model=list[CategoryResponse])
def search_categories(
    gender: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    business: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    is_leaf: bool | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    session: Session = Depends(get_session),
):
    service = get_category_query_service(session)
    query = GetCategoriesByConstraintsQuery(
        gender=gender,
        direction=direction,
        business=business,
        brand=brand,
        is_leaf=is_leaf,
        limit=limit,
    )
    categories = service.get_categories_by_constraints(query)

    return [
        CategoryResponse(
            id=c.id,
            name=c.name,
            level=c.level,
            parent_id=c.parent_id,
            is_leaf=c.is_leaf,
            gender=c.gender,
            direction=c.direction,
            brand=c.brand,
            business=c.business,
            keywords=list(c.keywords) if c.keywords else [],
        )
        for c in categories
    ]
