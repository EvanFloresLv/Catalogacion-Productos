# -----------------------------------------------------------------
# Schemas — Products
# -----------------------------------------------------------------
from __future__ import annotations

from pydantic import BaseModel, Field


# -----------------------------------------------------------------
# Responses
# -----------------------------------------------------------------
class SQLResponse(BaseModel):
    status: str
    data: list[dict] | None = None
    error: str | None = None


class SQLRequest(BaseModel):
    query: str = Field(..., description="The SQL query to execute", examples=["SELECT * FROM products"])