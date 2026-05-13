# -----------------------------------------------------------------
# Controller — Brands Endpoints
# -----------------------------------------------------------------
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from scripts.create_tables import create_tables
from scripts.reset_tables import reset_database

from infrastructure.web.schemas.sql_schemas import SQLRequest, SQLResponse

from infrastructure.web.dependencies import get_session

router = APIRouter(prefix="/sql", tags=["SQL"])



# -----------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------
@router.post("/execute")
def execute_sql(body: SQLRequest, session: Session = Depends(get_session)):
    try:
        result = session.execute(text(body.query))
        session.commit()
        rows = [dict(row._mapping) for row in result] if result.returns_rows else []
        return {"status": "success", "data": rows}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# @router.get("/create_tables")
# def create_tables_endpoint(session: Session = Depends(get_session)):
#     try:
#         # Call the function to create tables
#         create_tables()
#         return {"status": "success"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.get("/reset_tables")
# def reset_tables_endpoint(session: Session = Depends(get_session)):
#     try:
#         # Call the function to reset tables
#         reset_database()
#         return {"status": "success"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
