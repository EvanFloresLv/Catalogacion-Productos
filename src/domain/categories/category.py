# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import CategoryNameError


@dataclass(frozen=True)
class Category:
    id: UUID
    name: str
    parent_id: UUID | None

    @staticmethod
    def create(name: str, parent_id: UUID | None = None) -> Category:
        name = name.strip()

        if not name:
            raise CategoryNameError("Category name cannot be empty.")

        if len(name) > 100:
            raise CategoryNameError("Category name cannot exceed 100 characters.")

        return Category(
            id=uuid4(),
            name=name,
            parent_id=parent_id
        )