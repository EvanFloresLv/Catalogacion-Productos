# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base

if TYPE_CHECKING:
    from infrastructure.persistence.postgresql.models.category_model import CategoryModel


class CategoryProfileModel(Base):
    __tablename__ = "category_profiles"

    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    gender: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    direction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    business: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
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