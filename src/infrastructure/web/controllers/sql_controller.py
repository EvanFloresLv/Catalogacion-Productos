# -----------------------------------------------------------------
# Controller — Brands Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from scripts.create_tables import create_tables
from scripts.reset_tables import reset_tables

from infrastructure.web.dependencies import get_session

router = APIRouter(prefix="/sql", tags=["SQL"])

# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/execute")
def execute_sql(query: str, session: Session = Depends(get_session)):
    try:
        result = session.execute(query)
        session.commit()
        return {"status": "success", "data": result}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/create_tables")
def create_tables_endpoint(session: Session = Depends(get_session)):
    try:
        # Call the function to create tables
        create_tables()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reset_tables")
def reset_tables_endpoint(session: Session = Depends(get_session)):
    try:
        # Call the function to reset tables
        reset_tables()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
