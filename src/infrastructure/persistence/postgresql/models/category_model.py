# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations
from uuid import UUID as PyUUID
from typing import Optional, TYPE_CHECKING

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, ForeignKey, Text, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base

if TYPE_CHECKING:
    from infrastructure.persistence.postgresql.models.category_profile_model import CategoryProfileModel


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[PyUUID] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)

    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business: Mapped[str | None] = mapped_column(String(100), nullable=True)

    semantic_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    keywords_json: Mapped[list[str]] = mapped_column(Text, nullable=False)

    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("categories.id"),
        nullable=True,
    )

    parent: Mapped["CategoryModel | None"] = relationship(
        "CategoryModel",
        remote_side="[CategoryModel.id]",
        uselist=False,
        lazy="selectin",
    )

    profile: Mapped[Optional["CategoryProfileModel"]] = relationship(
        "CategoryProfileModel",
        back_populates="category",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("semantic_hash", name="uq_categories_semantic_hash"),
    )