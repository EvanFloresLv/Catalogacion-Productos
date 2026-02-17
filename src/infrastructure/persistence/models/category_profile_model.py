# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.db import Base
from infrastructure.persistence.models.category_model import CategoryModel


class CategoryProfileModel(Base):
    __tablename__ = "category_profiles"

    category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("categories.id"),
        primary_key=True,
    )

    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)

    allowed_genders_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_business_types_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped["CategoryModel"] = relationship("CategoryModel")
