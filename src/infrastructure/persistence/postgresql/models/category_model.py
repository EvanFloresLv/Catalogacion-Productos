# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, ForeignKey, UniqueConstraint, Integer, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base
from infrastructure.persistence.postgresql.models.brand_model import BrandModel


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    semantic_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    keywords = Column(JSONB, nullable=False, default=list)

    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_leaf: Mapped[bool | None] = mapped_column(nullable=True)
    group_articles: Mapped[list[str]] = mapped_column(JSONB, nullable=True, default=list)

    brand_id: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("brands.name"),
        nullable=True
    )

    brand: Mapped[BrandModel | None] = relationship(
        "BrandModel",
        foreign_keys=[brand_id],
        lazy="selectin",
    )

    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("categories.id"),
        nullable=True,
    )

    parent: Mapped[CategoryModel | None] = relationship(
        "CategoryModel",
        remote_side="[CategoryModel.id]",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("id", "direction", name="uq_categories_id_direction"),
    )