# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID as PyUUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base
from infrastructure.persistence.postgresql.models.category_model import CategoryModel


class CategoryProfileModel(Base):
    __tablename__ = "category_profiles"

    # store category_id as bytes (BLOB) to match CategoryModel.id
    category_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        primary_key=True,
        nullable=False,
    )


    allowed_genders_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_business_types_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # one-to-one relationship to CategoryModel
    category: Mapped["CategoryModel"] = relationship("CategoryModel", uselist=False)