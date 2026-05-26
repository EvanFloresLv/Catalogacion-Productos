# ---------------------------------------------------------------------
# In-Memory Embedding Repository — NumPy-based similarity search
# ---------------------------------------------------------------------
from __future__ import annotations

import logging
import threading
from typing import List, Tuple, Optional
from dataclasses import fields

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.entities.embedding import Embedding
from domain.repositories.embedding_repository import EmbeddingRepository

from infrastructure.persistence.postgresql.session import SessionLocal
from infrastructure.persistence.postgresql.repositories.embedding_repository_pg import EmbeddingRepositoryPG
from infrastructure.persistence.postgresql.models.embedding_model import EmbeddingModel

logger = logging.getLogger(__name__)


class InMemoryEmbeddingRepository(EmbeddingRepository):
    """
    Loads all embeddings into memory on first use, then performs
    similarity search via NumPy vectorized cosine similarity.

    ~300MB for 100K embeddings (768-dim float32).
    Search time: <5ms vs 50-200ms with DB.
    """

    _lock = threading.Lock()
    _loaded = False

    # Shared across all instances (singleton data)
    _category_ids: list[str] = []
    _vectors: Optional[np.ndarray] = None  # shape: (N, 768)
    _cat_id_to_indices: dict[str, list[int]] = {}
    _entities: list[Embedding] = []

    def __init__(self, session: Session):
        self._session = session
        self._ensure_loaded()

    # -----------------------------------------------------------------
    # One-time load
    # -----------------------------------------------------------------
    def _ensure_loaded(self) -> None:
        if InMemoryEmbeddingRepository._loaded:
            return

        with InMemoryEmbeddingRepository._lock:
            if InMemoryEmbeddingRepository._loaded:
                return
            self._load_all()
            InMemoryEmbeddingRepository._loaded = True

    def _load_all(self) -> None:
        logger.info("Loading all embeddings into memory...")

        rows = self._session.execute(
            select(EmbeddingModel)
        ).scalars().all()

        category_ids = []
        vectors = []
        entities = []
        cat_id_to_indices: dict[str, list[int]] = {}

        for i, row in enumerate(rows):
            cat_id = row.category_id
            vec = list(row.vector) if hasattr(row.vector, '__iter__') else row.vector

            category_ids.append(cat_id)
            vectors.append(vec)
            entities.append(self._to_entity(row))

            cat_id_to_indices.setdefault(cat_id, []).append(i)

        InMemoryEmbeddingRepository._category_ids = category_ids
        InMemoryEmbeddingRepository._vectors = np.array(vectors, dtype=np.float32) if vectors else np.empty((0, 768), dtype=np.float32)
        InMemoryEmbeddingRepository._entities = entities
        InMemoryEmbeddingRepository._cat_id_to_indices = cat_id_to_indices

        # Pre-normalize for cosine similarity
        norms = np.linalg.norm(InMemoryEmbeddingRepository._vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        InMemoryEmbeddingRepository._vectors = InMemoryEmbeddingRepository._vectors / norms

        logger.info(f"Loaded {len(rows)} embeddings into memory ({InMemoryEmbeddingRepository._vectors.nbytes / 1024 / 1024:.1f} MB)")

    @classmethod
    def reload(cls, session: Session) -> None:
        """Force reload synchronously."""
        with cls._lock:
            cls._loaded = False
        cls(session)

    @classmethod
    def invalidate_async(cls, session_factory) -> None:
        def _reload():
            try:
                session = session_factory()
                try:
                    with cls._lock:
                        cls._loaded = False
                    cls(session)
                    logger.info("In-memory embeddings reloaded (background).")
                finally:
                    session.close()
            except Exception:
                logger.exception("Background embedding reload failed.")

        thread = threading.Thread(target=_reload, daemon=True)
        thread.start()

    # -----------------------------------------------------------------
    # Similarity Search (vectorized NumPy)
    # -----------------------------------------------------------------
    def search_similar(
        self,
        query_vector: List[float],
        category_ids: List[str],
        limit: int = 10,
    ) -> List[Tuple[Embedding, float]]:

        if not query_vector:
            raise ValueError("query_vector cannot be empty")

        vectors = InMemoryEmbeddingRepository._vectors
        entities = InMemoryEmbeddingRepository._entities

        if vectors is None or len(vectors) == 0:
            return []

        # Filter indices by category_ids
        if category_ids:
            indices = []
            for cid in category_ids:
                indices.extend(InMemoryEmbeddingRepository._cat_id_to_indices.get(cid, []))
            if not indices:
                return []
            indices = np.array(indices, dtype=np.int64)
            subset = vectors[indices]
        else:
            indices = None
            subset = vectors

        # Normalize query vector
        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        # Vectorized cosine similarity (dot product of normalized vectors)
        similarities = subset @ q

        # Top-k
        k = min(limit, len(similarities))
        top_k_local = np.argpartition(similarities, -k)[-k:]
        top_k_local = top_k_local[np.argsort(similarities[top_k_local])[::-1]]

        results: List[Tuple[Embedding, float]] = []
        for local_idx in top_k_local:
            global_idx = int(indices[local_idx]) if indices is not None else int(local_idx)
            score = max(0.0, min(1.0, float(similarities[local_idx])))
            results.append((entities[global_idx], score))

        return results

    # -----------------------------------------------------------------
    # Pass-through write operations (delegate to DB via session)
    # -----------------------------------------------------------------
    def save(self, embedding: Embedding) -> None:
        EmbeddingRepositoryPG(self._session).save(embedding)
        self._schedule_reload()

    def save_batch(self, embeddings: list[Embedding]) -> list[Embedding]:
        result = EmbeddingRepositoryPG(self._session).save_batch(embeddings)
        self._schedule_reload()
        return result

    def _schedule_reload(self) -> None:
        try:
            InMemoryEmbeddingRepository.invalidate_async(SessionLocal)
        except Exception:
            InMemoryEmbeddingRepository._loaded = False

    def get_by_category_id(self, category_id) -> Optional[Embedding]:
        indices = InMemoryEmbeddingRepository._cat_id_to_indices.get(str(category_id), [])
        return InMemoryEmbeddingRepository._entities[indices[0]] if indices else None

    def get_by_category_ids(self, category_ids) -> list[Embedding]:
        results = []
        for cid in category_ids:
            indices = InMemoryEmbeddingRepository._cat_id_to_indices.get(str(cid), [])
            results.extend(InMemoryEmbeddingRepository._entities[i] for i in indices)
        return results

    def find_by_hashes(self, hashes: List[str]) -> List[Embedding]:
        return EmbeddingRepositoryPG(self._session).find_by_hashes(hashes)

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _to_entity(model: EmbeddingModel) -> Embedding:
        init_field_names = {f.name for f in fields(Embedding) if f.init}
        return Embedding(
            **{field: getattr(model, field) for field in init_field_names if hasattr(model, field)}
        )
