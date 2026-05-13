# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import BLOB

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.db import Base


def uuid_to_bytes(u: UUID) -> bytes:
    return u.bytes


def bytes_to_uuid(b: bytes) -> UUID:
    return UUID(bytes=b)


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(BLOB, primary_key=True, default=uuid_to_bytes)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(BLOB, ForeignKey("categories.id"), nullable=True)