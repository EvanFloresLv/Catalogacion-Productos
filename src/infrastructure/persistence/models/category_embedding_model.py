# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import BLOB

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.db import Base


class CategoryEmbeddingModel(Base):
    __tablename__ = "category_embeddings"

    category_id: Mapped[bytes] = mapped_column(BLOB, primary_key=True)
    vector_blob: Mapped[list[float]] = mapped_column(Text, nullable=False)