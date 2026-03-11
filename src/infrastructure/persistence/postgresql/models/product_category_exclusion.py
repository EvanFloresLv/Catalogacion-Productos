# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import ForeignKey, Text, String, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base


class ProductCategoryExclusionModel(Base):
    __tablename__ = "product_category_exclusions"

    # Product composite key references
    product_sku: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        nullable=False,
    )

    # Category reference
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Composite foreign key constraint
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_sku"],
            ["products.sku"],
            ondelete="CASCADE"
        ),
    )