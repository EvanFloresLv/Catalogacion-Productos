# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from infrastructure.persistence.db import Base


class FaissIdMapModel(Base):
    __tablename__ = "faiss_id_map"

    faiss_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_uuid: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    __table_args__ = (
        UniqueConstraint("entity_uuid", name="uq_faiss_entity_uuid"),
    )