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
from .errors import ProductTitleError


@dataclass(frozen=True)
class Product:
    id: UUID
    title: str
    description: str
    keywords: list[str]


    @staticmethod
    def create(
        title: str,
        description: str,
        keywords: list[str]
    ) -> Product:
        title = title.strip()

        if not title:
            raise ProductTitleError("Product title cannot be empty.")

        description = (description or "").strip()
        keywords = [k.strip() for k in keywords if k.strip()]

        return Product(
            id=uuid4(),
            title=title,
            description=description,
            keywords=keywords
    )


    def to_embedding_text(self) -> str:
        keywords = ", ".join(self.keywords)
        return f"TITLE: {self.title}\nDESCRIPTION: {self.description}\nKEYWORDS: {keywords}"