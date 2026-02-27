# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from typing import Optional, List, Tuple

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.embeddings.embedding import Embedding
from application.ports.embedding_repository import EmbeddingRepository
from infrastructure.persistence.postgresql.models.embedding_model import EmbeddingModel

from utils.vectors import normalize_vector


class EmbeddingRepositoryPG(EmbeddingRepository):

    def __init__(self, session: Session, expected_dimension: int = 768):
        self.session = session
        self.expected_dimension = expected_dimension

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, embedding: Embedding) -> None:
        vec = self._prepare_vector(embedding.vector)

        stmt = insert(EmbeddingModel).values(
            id=embedding.id,
            category_id=embedding.category_id,
            vector=vec,
            content_hash=embedding.content_hash,
            dimension=len(vec),
            created_at=embedding.created_at,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["category_id", "content_hash"],
            set_={
                "vector": stmt.excluded.vector,
                "dimension": stmt.excluded.dimension,
            },
        )

        self.session.execute(stmt)
        self.session.commit()

    # -------------------------------------------------------------

    def save_batch(self, embeddings: list[Embedding]) -> None:
        if not embeddings:
            return

        values = []
        for e in embeddings:
            vec = self._prepare_vector(e.vector)

            values.append(
                {
                    "id": e.id,
                    "category_id": e.category_id,
                    "vector": vec,
                    "content_hash": e.content_hash,
                    "dimension": len(vec),
                    "created_at": e.created_at,
                }
            )

        stmt = insert(EmbeddingModel).values(values)

        stmt = stmt.on_conflict_do_update(
            index_elements=["category_id", "content_hash"],
            set_={
                "vector": stmt.excluded.vector,
                "dimension": stmt.excluded.dimension,
            },
        )

        self.session.execute(stmt)
        self.session.commit()

    # ============================================================
    # Retrieval
    # ============================================================

    def get_by_category_id(self, category_id: UUID) -> Optional[Embedding]:
        stmt = select(EmbeddingModel).where(
            EmbeddingModel.category_id == category_id
        )

        result = self.session.execute(stmt).scalars().first()

        return self._to_entity(result) if result else None

    # -------------------------------------------------------------

    def get_by_category_ids(self, category_ids: list[UUID]) -> list[Embedding]:
        if not category_ids:
            return []

        stmt = select(EmbeddingModel).where(
            EmbeddingModel.category_id.in_(category_ids)
        )

        results = self.session.execute(stmt).scalars().all()

        return [self._to_entity(r) for r in results]

    # ============================================================
    # Semantic Search (Improved Similarity)
    # ============================================================

    def search_similar(
        self,
        query_vector: list[float],
        limit: int = 10,
    ) -> List[Tuple[Embedding, float]]:

        if not query_vector:
            raise ValueError("query_vector cannot be empty")

        if limit <= 0:
            raise ValueError("limit must be > 0")

        q_vec = self._prepare_vector(query_vector)

        # Convert distance → similarity score
        distance_expr = EmbeddingModel.vector.cosine_distance(q_vec)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        stmt = (
            select(EmbeddingModel, similarity_expr)
            .order_by(similarity_expr.desc())  # higher similarity first
            .limit(limit)
        )

        rows = self.session.execute(stmt).all()

        results: List[Tuple[Embedding, float]] = []

        for model, similarity in rows:
            results.append(
                (self._to_entity(model), float(similarity))
            )

        return results

    # ============================================================
    # Internal helpers
    # ============================================================

    def _prepare_vector(self, vector: list[float]) -> list[float]:
        if not vector:
            raise ValueError("Embedding vector cannot be empty")

        vec = normalize_vector(list(vector))

        if len(vec) != self.expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch. "
                f"Expected {self.expected_dimension}, got {len(vec)}"
            )

        return vec

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: EmbeddingModel) -> Embedding:
        return Embedding(
            id=model.id,
            category_id=model.category_id,
            vector=model.vector,
            content_hash=model.content_hash,
            dimension=model.dimension,
            created_at=model.created_at,
        )