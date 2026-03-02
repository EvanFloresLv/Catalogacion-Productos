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
    bussiness: str

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
        bussiness: str | None = None,
        parent_id: str | None = None
    ) -> Category:
        name = name.strip()
        description = description.strip()

        if not id or not url or not name or not description:
            raise CategoryNameError("Category ID, URL, name, and description cannot be empty.")

        if len(name) > 100:
            raise CategoryNameError("Category name cannot exceed 100 characters.")

        return Category(
            id=id,
            parent_id=parent_id,
            name=name,
            level=level,
            description=description,
            brand=brand,
            direction=direction,
            bussiness=bussiness,
            semantic_hash=SemanticHash.from_text(description).value,
            keywords=keywords,
        )


    def to_embedding_text(self) -> str:
        keywords = ", ".join(self.keywords)
        return f"TÍTULO: {self.name}\nDESCRIPCIÓN: {self.description}\nPALABRAS CLAVE: {keywords}"


    def with_id(self, new_id: str) -> Category:
        return replace(self, id=new_id)