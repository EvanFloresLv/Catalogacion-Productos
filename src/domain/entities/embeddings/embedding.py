# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from __future__ import annotations

from uuid import uuid4, UUID

from dataclasses import dataclass
from datetime import datetime
from typing import List

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Embedding:
    id: UUID
    category_id: UUID
    vector: List[float]
    content_hash: str
    dimension: int
    created_at: datetime


    @staticmethod
    def create(category_id: UUID, vector: List[float], content_hash: str) -> Embedding:
        return Embedding(
            id=uuid4(),
            category_id=category_id,
            vector=vector,
            content_hash=content_hash,
            dimension=len(vector),
            created_at=datetime.now(),
        )