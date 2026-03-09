# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Tuple

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

    gender: str | None
    business_type: str | None

    @staticmethod
    def create(
        title: str,
        description: str,
        keywords: list[str],
        gender: str | None = None,
        business_type: str | None = None
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
            keywords=keywords,
            gender=gender,
            business_type=business_type
        )


    @staticmethod
    def _build_embedding_text(
        name: str,
        description: str,
        keywords: Tuple[str, ...],
    ) -> str:
        return (
            f"TÍTULO: {name}\n"
            f"DESCRIPCIÓN: {description}\n"
            f"PALABRAS CLAVE: {', '.join(keywords)}"
        )

    def to_embedding_text(self) -> str:
        return self._build_embedding_text(
            name=self.title,
            description=self.description or "",
            keywords=tuple(self.keywords)
        )