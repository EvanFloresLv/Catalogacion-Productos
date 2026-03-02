# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations
from uuid import UUID as PyUUID
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base

if TYPE_CHECKING:
    from infrastructure.persistence.postgresql.models.category_model import CategoryModel


class CategoryProfileModel(Base):
    __tablename__ = "category_profiles"

    category_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    allowed_genders: Mapped[list[str] | None] = mapped_column(
        ARRAY(TEXT),
        nullable=True,
        default=list,
    )

    allowed_business_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(TEXT),
        nullable=True,
        default=list,
    )

    category: Mapped["CategoryModel"] = relationship(
        "CategoryModel",
        back_populates="profile",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("category_id"),
    )