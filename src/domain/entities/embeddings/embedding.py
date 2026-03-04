# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from __future__ import annotations

from uuid import uuid4, UUID

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Tuple, Any

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Embedding:

    # ---------------------------------------------------------
    # Required fields (NO defaults)
    # ---------------------------------------------------------
    category_id: str
    vector: Tuple[float, ...]
    content_hash: str

    # ---------------------------------------------------------
    # Optional fields (defaults allowed)
    # ---------------------------------------------------------
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------
    # Computed (not in __init__)
    # ---------------------------------------------------------
    dimension: int = field(init=False)

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> "Embedding":

        init_fields = {f.name for f in fields(cls) if f.init}

        # Prevent injection of computed fields
        forbidden = {"dimension"}
        if forbidden & set(data.keys()):
            raise ValueError("dimension is computed and cannot be provided.")

        # Reject unknown fields
        unknown = set(data.keys()) - init_fields
        if unknown:
            raise ValueError(f"Unknown fields: {unknown}")

        vector = data.get("vector")
        if not vector:
            raise ValueError("vector is required.")

        # Normalize vector → immutable tuple
        normalized_vector = tuple(float(v) for v in vector)

        if not normalized_vector:
            raise ValueError("vector cannot be empty.")

        data["vector"] = normalized_vector

        obj = cls(**data)

        # Inject computed dimension safely
        object.__setattr__(obj, "dimension", len(normalized_vector))

        return obj


    def __post_init__(self):
        object.__setattr__(self, "dimension", len(self.vector))