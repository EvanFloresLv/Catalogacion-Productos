# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations
from uuid import UUID, uuid4

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base


class BrandModel(Base):
    __tablename__ = "brands"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    business: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)