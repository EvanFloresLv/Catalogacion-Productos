# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from typing import Optional, List, Tuple
from dataclasses import fields

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
from infrastructure.persistence.postgresql.models.embedding_model import (
    EmbeddingModel,
)


class EmbeddingRepositoryPG(EmbeddingRepository):

    DEFAULT_BATCH_SIZE = 1000

    def __init__(
        self,
        session: Session,
        expected_dimension: int,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.session = session
        self.expected_dimension = expected_dimension
        self.batch_size = batch_size

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, embedding: Embedding) -> None:
        row = self._build_row(embedding)

        stmt = insert(EmbeddingModel).values(**row)

        stmt = stmt.on_conflict_do_update(
            index_elements=["category_id", "content_hash"],
            set_={
                "vector": stmt.excluded.vector,
                "dimension": stmt.excluded.dimension,
            },
        )

        self.session.execute(stmt)
        self.session.flush()

    # -------------------------------------------------------------

    def save_batch(self, embeddings: list[Embedding]) -> None:
        if not embeddings:
            return

        for i in range(0, len(embeddings), self.batch_size):
            chunk = embeddings[i : i + self.batch_size]

            rows = [self._build_row(e) for e in chunk]

            stmt = insert(EmbeddingModel).values(rows)

            stmt = stmt.on_conflict_do_update(
                index_elements=["category_id", "content_hash"],
                set_={
                    "vector": stmt.excluded.vector,
                    "dimension": stmt.excluded.dimension,
                },
            )

            self.session.execute(stmt)

        self.session.flush()

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
    # Semantic Search
    # ============================================================

    def search_similar(
        self,
        query_vector: list[float],
        category_ids: list[UUID],
        limit: int = 10,
    ) -> List[Tuple[Embedding, float]]:

        if not query_vector:
            raise ValueError("query_vector cannot be empty")

        if limit <= 0:
            raise ValueError("limit must be > 0")

        self._validate_dimension(query_vector)

        similarity_expr = (
            (1.0 - EmbeddingModel.vector.cosine_distance(query_vector))
            .label("similarity")
        )

        stmt = select(EmbeddingModel, similarity_expr)

        if category_ids:
            stmt = stmt.where(
                EmbeddingModel.category_id.in_(category_ids)
            )

        stmt = (
            stmt
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        rows = self.session.execute(stmt).all()

        results: List[Tuple[Embedding, float]] = []

        for model, similarity in rows:
            score = max(0.0, min(1.0, float(similarity)))
            results.append((self._to_entity(model), score))

        return results

    # ============================================================
    # Internal Helpers
    # ============================================================

    @staticmethod
    def _build_row(embedding: Embedding) -> dict:
        """
        Build dynamic insert row from Embedding entity.
        Avoids hardcoding attribute names.
        """

        row = {}

        for field in fields(embedding):
            row[field.name] = getattr(embedding, field.name)

        # Ensure dimension consistency
        vector = row.get("vector")

        if not vector:
            raise ValueError("Embedding vector cannot be empty")

        row["dimension"] = len(vector)

        return row

    # -------------------------------------------------------------

    def _validate_dimension(self, vector: list[float]) -> None:
        if not vector:
            raise ValueError("Embedding vector cannot be empty")

        if len(vector) != self.expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch. "
                f"Expected {self.expected_dimension}, got {len(vector)}"
            )

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: EmbeddingModel) -> Embedding:
        field_names = {f.name for f in fields(Embedding)}

        return Embedding(
            **{field: getattr(model, field) for field in field_names}
        )