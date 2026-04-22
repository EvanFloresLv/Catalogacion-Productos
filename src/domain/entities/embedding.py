# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from __future__ import annotations

from uuid import uuid4, UUID

from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple, Any

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from utils.domain_validatons import validate_entity_fields


@dataclass(frozen=True, slots=True)
class Embedding:

    # ---------------------------------------------------------
    # Required fields (NO defaults)
    # ---------------------------------------------------------
    category_id: str
    vector: Tuple[float, ...]
    content_hash: str
    dimension: int

    # ---------------------------------------------------------
    # Optional fields (defaults allowed)
    # ---------------------------------------------------------
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> Embedding:

        # Prevent injection of computed fields
        forbidden = {"dimension"}

        if forbidden & set(data.keys()):
            raise ValueError("dimension is computed and cannot be provided.")

        normalized = validate_entity_fields(cls, data, required_fields={"category_id", "vector", "content_hash"})
        normalized.pop("dimension", None)

        return cls(
            **data,
            dimension=len(normalized["vector"])
        )


    def __post_init__(self):
        object.__setattr__(self, "dimension", len(self.vector))

if __name__ == "__main__":

    embedding = Embedding.create(
        category_id="123",
        vector=(0.1, 0.2, 0.3),
        content_hash="abc123",
        created_at=datetime(2024, 6, 1, 12, 0, 0)
    )

    print(embedding)