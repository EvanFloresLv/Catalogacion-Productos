# -----------------------------------------------------------------
# Controller — Brands Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

import pandas as pd
import tempfile
import shutil

from infrastructure.web.dependencies import get_session
from infrastructure.web.schemas.brands_schemas import (
    BrandResponse,
    LoadBrandsResponse,
)
from infrastructure.persistence.postgresql.repositories.brand_repository_pg import (
    BrandRepositoryPG,
)
from application.use_cases.brands.load_brands import LoadBrandsCommand, LoadBrandsUseCase
from config.composition_root import create_unit_of_work

router = APIRouter(prefix="/brands", tags=["Brands"])


# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/load", response_model=LoadBrandsResponse)
def load_brands_from_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    data = pd.read_excel(tmp_path, sheet_name=0)

    repo = BrandRepositoryPG(session)
    uow = create_unit_of_work(session)
    use_case = LoadBrandsUseCase(repo=repo, uow=uow)
    result = use_case.execute(LoadBrandsCommand(data=data))

    return LoadBrandsResponse(brands_count=len(result) if result else 0)


@router.get("/", response_model=list[BrandResponse])
def get_all_brands(
    session: Session = Depends(get_session),
):
    repo = BrandRepositoryPG(session)
    brands = repo.get_all()
    return [BrandResponse.from_entity(b) for b in brands]


@router.get("/search", response_model=list[BrandResponse])
def get_brands_by_business(
    business: str = Query(..., min_length=1),
    session: Session = Depends(get_session),
):
    repo = BrandRepositoryPG(session)
    brands = repo.get_by_business(business)
    return [BrandResponse.from_entity(b) for b in brands]


@router.get("/{name}", response_model=BrandResponse)
def get_brand_by_name(
    name: str,
    session: Session = Depends(get_session),
):
    repo = BrandRepositoryPG(session)
    brand = repo.get_by_name(name)

    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{name}' not found.")

    return BrandResponse.from_entity(brand)
