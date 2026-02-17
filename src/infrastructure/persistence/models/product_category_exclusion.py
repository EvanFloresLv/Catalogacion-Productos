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
from infrastructure.persistence.models import CategoryModel, ProductModel


class ProductCategoryExclusionModel(Base):
    __tablename__ = "product_category_exclusions"

    product_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("products.id"),
        primary_key=True,
    )

    category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("categories.id"),
        primary_key=True,
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    product: Mapped["ProductModel"] = relationship("ProductModel")
    category: Mapped["CategoryModel"] = relationship("CategoryModel")
