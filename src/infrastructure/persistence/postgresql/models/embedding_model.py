# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from uuid import UUID
from datetime import datetime

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base


class EmbeddingModel(Base):
    __tablename__ = "embeddings"

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "content_hash",
            name="uq_embeddings_category_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True
    )

    category_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vector: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False
    )

    content_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )

    dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
