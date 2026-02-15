# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import pickle
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.category_embedding_repository import CategoryEmbeddingRepository
from infrastructure.persistence.models.category_embedding_model import CategoryEmbeddingModel
from infrastructure.persistence.utils.uuid import uuid_to_bytes, bytes_to_uuid


class SQLCategoryEmbeddingRepository(CategoryEmbeddingRepository):

    def __init__(self, session: Session):
        self.session = session


    def upsert(
        self,
        category_id: UUID,
        vector: list[float]
    ) -> None:
        blob = pickle.dumps(vector)
        category_embedding = CategoryEmbeddingModel(
            category_id=uuid_to_bytes(category_id),
            vector_blob=blob
        )
        self.session.merge(category_embedding)
        self.session.commit()


    def get_all(self) -> list[tuple[UUID, list[float]]]:
        rows = self.session.execute(select(CategoryEmbeddingModel)).scalars().all()
        out: list[tuple[UUID, list[float]]] = []

        for row in rows:
            out.append((
                bytes_to_uuid(row.category_id),
                pickle.loads(row.vector_blob)
            ))

        return out


    def delete_all(self) -> None:
        self.session.execute(delete(CategoryEmbeddingModel))
        self.session.commit()