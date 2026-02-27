# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import CategoryNameError
from domain.value_objects.semantic_hash import SemanticHash


@dataclass(frozen=True)
class Category:
    id: UUID
    name: str
    semantic_hash: str
    description: str
    keywords: list[str]
    parent_id: UUID | None


    @staticmethod
    def create(
        name: str,
        description: str,
        keywords: list[str],
        parent_id: UUID | None = None
    ) -> Category:
        name = name.strip()
        description = description.strip()

        if not name:
            raise CategoryNameError("Category name cannot be empty.")

        if not description:
            raise CategoryNameError("Category description cannot be empty.")

        if len(name) > 100:
            raise CategoryNameError("Category name cannot exceed 100 characters.")

        return Category(
            id=uuid4(),
            name=name,
            description=description,
            semantic_hash=SemanticHash.from_text(description).value,
            keywords=keywords,
            parent_id=parent_id
        )


    def to_embedding_text(self) -> str:
        keywords = ", ".join(self.keywords)
        return f"TITLE: {self.name}\nDESCRIPTION: {self.description}\nKEYWORDS: {keywords}"


    def with_id(self, new_id: UUID) -> Category:
        return replace(self, id=new_id)