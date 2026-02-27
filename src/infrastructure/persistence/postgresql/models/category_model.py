# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID as PyUUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base


class CategoryModel(Base):
    __tablename__ = "categories"

    # Persist UUIDs as bytes in SQLite BLOB columns; convert in repo layer.
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    semantic_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)

    parent_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
    )

    parent: Mapped["CategoryModel | None"] = relationship(
        "CategoryModel",
        remote_side=[id],
        backref="children",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "semantic_hash",
            name="uq_categories_semantic_hash",
        ),
    )