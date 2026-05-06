# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, Text, ARRAY, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.postgresql.base import Base


class ProductModel(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(50), nullable=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False)

    business: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False)

    keywords = Column(JSONB, nullable=False, default=list)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    article_group = Column(JSONB, nullable=False, default=list)

    description: Mapped[str] = mapped_column(Text, nullable=True)
