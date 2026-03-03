# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, replace

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
    id: str
    parent_id: str | None

    name: str
    level: int
    description: str
    url: str
    keywords: list[str]

    brand: str
    direction: str
    business: str

    semantic_hash: str

    @staticmethod
    def create(
        id: str,
        name: str,
        level: int,
        description: str,
        keywords: list[str],
        url: str | None = None,
        brand: str | None = None,
        direction: str | None = None,
        business: str | None = None,
        parent_id: str | None = None
    ) -> Category:
        name = name.strip()
        description = description.strip()

        if not id:
            raise CategoryNameError("Category ID cannot be empty.")

        if not name:
            raise CategoryNameError("Category name cannot be empty.")

        if not isinstance(level, int) or level < 1:
            raise CategoryNameError("Category level must be a positive integer.")

        if len(name) > 100:
            raise CategoryNameError("Category name cannot exceed 100 characters.")

        return Category(
            id=id,
            parent_id=parent_id,
            name=name,
            level=level,
            description=description,
            url=url,
            brand=brand,
            direction=direction,
            business=business,
            semantic_hash=SemanticHash.from_text(description).value,
            keywords=keywords,
        )


    def to_embedding_text(self) -> str:
        keywords = ", ".join(self.keywords)
        return f"TÍTULO: {self.name}\nDESCRIPCIÓN: {self.description}\nPALABRAS CLAVE: {keywords}"


    def with_id(self, id: str) -> Category:
        return replace(self, id=id)