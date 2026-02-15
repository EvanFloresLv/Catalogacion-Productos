# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations
from pathlib import Path
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import numpy as np
import faiss

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.faiss_id_mapper import FaissIdMapper


class FaissVectorIndex:

    def __init__(self, mapper: FaissIdMapper, index_path: str):
        self.mapper = mapper
        self.index_path = Path(index_path)

        self._index: faiss.Index | None = None
        self._dim: int | None = None


    def reset(self, dimension: int) -> None:
        self._dim = dimension
        base = faiss.IndexFlatIP(dimension)  # cosine via normalized vectors
        self._index = faiss.IndexIDMap2(base)


    def add(self, item_id: UUID, vector: list[float]) -> None:
        if self._index is None:
            raise RuntimeError("FAISS index not initialized. Call reset() first.")

        faiss_id = self.mapper.get_or_create_faiss_id(item_id)

        v = np.array([vector], dtype="float32")
        ids = np.array([faiss_id], dtype="int64")
        self._index.add_with_ids(v, ids)


    def search(self, query: list[float], top_k: int) -> list[tuple[UUID, float]]:
        if self._index is None:
            raise RuntimeError("FAISS index not initialized. Call reset() first.")

        q = np.array([query], dtype="float32")
        scores, ids = self._index.search(q, top_k)

        out: list[tuple[UUID, float]] = []
        for score, faiss_id in zip(scores[0], ids[0]):
            if int(faiss_id) == -1:
                continue

            uuid_ = self.mapper.get_uuid(int(faiss_id))
            if uuid_ is None:
                continue

            out.append((uuid_, float(score)))

        return out


    def save(self) -> None:
        if self._index is None:
            raise RuntimeError("FAISS index not initialized.")

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path))


    def load(self) -> bool:
        if not self.index_path.exists():
            return False

        self._index = faiss.read_index(str(self.index_path))
        self._dim = self._index.d
        return True


    def dimension(self) -> int | None:
        return self._dim
