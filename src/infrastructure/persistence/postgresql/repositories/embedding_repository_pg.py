# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from typing import Optional, List, Tuple
from dataclasses import fields

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.embedding import Embedding
from domain.repositories.embedding_repository import EmbeddingRepository
from infrastructure.persistence.postgresql.models.embedding_model import (
    EmbeddingModel,
)


class EmbeddingRepositoryPG(EmbeddingRepository):
    """
    pgvector-backed EmbeddingRepository.

    Search uses the HNSW cosine index defined on ``embeddings.vector``.
    The runtime parameter ``hnsw.ef_search`` is set once per pooled
    connection by ``infrastructure.persistence.postgresql.session``
    (see ``_on_connect``); this keeps the GUC out of the
    application's transaction boundary and out of every search call.
    """

    DEFAULT_BATCH_SIZE = 1000

    # Over-fetch factor: HNSW can return candidates that are filtered
    # out by the ``category_id IN (...)`` predicate, so we ask for a
    # few extra rows and trim. 3× is enough for a few hundred allowed
    # categories and still small enough to keep p95 latency low.
    OVERFETCH_MULTIPLIER = 3

    def __init__(
        self,
        session: Session,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.session = session
        self.expected_dimension = EmbeddingModel.vector.type.dim
        self.batch_size = batch_size

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, embedding: Embedding) -> None:
        row = self._build_row(embedding)

        stmt = insert(EmbeddingModel).values(**row)

        stmt = stmt.on_conflict_do_update(
            constraint="uq_embeddings_category_hash",
            set_={
                "vector": stmt.excluded.vector,
                "dimension": stmt.excluded.dimension,
            },
        )

        self.session.execute(stmt)
        self.session.flush()

    # -------------------------------------------------------------

    def save_batch(self, embeddings: list[Embedding]) -> list[Embedding]:
        if not embeddings:
            return []

        all_results: list = []
        for i in range(0, len(embeddings), self.batch_size):
            chunk = embeddings[i : i + self.batch_size]

            # Defensive deduplication (CRITICAL)
            unique: dict[tuple[str, str], Embedding] = {}
            for e in chunk:
                key = (e.category_id, e.content_hash)
                unique[key] = e

            deduped_chunk = list(unique.values())
            rows = [self._build_row(e) for e in deduped_chunk]

            stmt = insert(EmbeddingModel).values(rows)

            stmt = stmt.on_conflict_do_update(
                constraint="uq_embeddings_category_hash",
                set_={
                    "vector": stmt.excluded.vector,
                    "dimension": stmt.excluded.dimension,
                },
            ).returning(EmbeddingModel)

            results = self.session.execute(stmt).scalars().all()
            self.session.flush()
            all_results.extend(results)

        return [self._to_entity(r) for r in all_results]

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

    # -------------------------------------------------------------

    def find_by_hashes(self, hashes: List[str]) -> List[Embedding]:
        if not hashes:
            return []

        stmt = (
            select(EmbeddingModel)
            .where(EmbeddingModel.content_hash.in_(hashes))
        )

        rows = self.session.execute(stmt).scalars().all()

        return [
            Embedding(
                category_id=row.category_id,
                vector=row.vector,
                content_hash=row.content_hash,
            )
            for row in rows
        ]

    # ============================================================
    # Semantic Search
    # ============================================================

    def search_similar(
        self,
        query_vector: list[float],
        category_ids: list[str],
        limit: int = 10,
    ) -> List[Tuple[Embedding, float]]:

        if not query_vector:
            raise ValueError("query_vector cannot be empty")

        if limit <= 0:
            raise ValueError("limit must be > 0")

        self._validate_dimension(query_vector)

        # Use cosine distance directly — the HNSW index on the column
        # optimizes this ordering, so we can let pgvector pick the
        # nearest neighbors with a single ORDER BY.
        distance_expr = EmbeddingModel.vector.cosine_distance(query_vector).label("distance")

        stmt = select(EmbeddingModel, distance_expr)

        if category_ids:
            stmt = stmt.where(
                EmbeddingModel.category_id.in_(category_ids)
            )
            # Over-fetch to compensate for post-filtering by
            # ``category_id IN (...)``. Without this trick HNSW can
            # return < ``limit`` rows that all happen to be in the
            # allowed set, lowering recall on the re-rank.
            fetch_limit = limit * self.OVERFETCH_MULTIPLIER
        else:
            fetch_limit = limit

        stmt = stmt.order_by(distance_expr.asc()).limit(fetch_limit)

        rows = self.session.execute(stmt).all()

        # Take the top ``limit`` by ascending distance. We do the trim
        # in Python (not SQL with a subquery) so that the HNSW index
        # is used for ordering and we don't pay for a sort node.
        results: List[Tuple[Embedding, float]] = []
        for model, distance in rows[:limit]:
            similarity = self._distance_to_similarity(distance)
            results.append((self._to_entity(model), similarity))

        return results

    # ============================================================
    # Diagnostics
    # ============================================================

    def count(self) -> int:
        """Total number of embeddings. Cheap (uses the PK index)."""
        return int(
            self.session.execute(
                select(func.count()).select_from(EmbeddingModel)
            ).scalar_one()
        )

    # ============================================================
    # Internal helpers
    # ============================================================

    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        # pgvector's ``<=>` returns cosine distance in [0, 2];
        # for normalized vectors the practical range is [0, 1]
        # and similarity = 1 - distance.
        return max(0.0, min(1.0, 1.0 - float(distance)))

    # -------------------------------------------------------------

    @staticmethod
    def _build_row(embedding: Embedding) -> dict:
        vector = embedding.vector

        if vector is None:
            raise ValueError(f"Vector is None for embedding {embedding.category_id}")

        vector_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)

        if not vector_list:
            raise ValueError(f"Empty vector for embedding {embedding.category_id}")

        return {
            "category_id": embedding.category_id,
            "vector": vector_list,
            "content_hash": embedding.content_hash,
            "dimension": len(vector_list),
        }

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
        init_field_names = {f.name for f in fields(Embedding) if f.init}

        return Embedding(
            **{field: getattr(model, field) for field in init_field_names if hasattr(model, field)}
        )
