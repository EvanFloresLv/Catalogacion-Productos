# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
from typing import Tuple, Any

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import CategoryNameError

from domain.value_objects.semantic_hash import SemanticHash
from utils.domain_validatons import validate_entity_fields, normalize_str


# -------------------------------------------------------------
# Entity
# -------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Category:

    # ---------------------------------------------------------
    # Required fields
    # ---------------------------------------------------------
    id: str
    name: str
    level: int

    # ---------------------------------------------------------
    # Optional fields
    # ---------------------------------------------------------
    parent_id: str | None = None
    is_leaf: bool | None = None

    description: str | None = None
    gender: str | None = None
    direction: str | None = None
    brand: str | None = None
    article_group: list[int] | None = None

    business: str = ""
    semantic_hash: str = ""

    # ---------------------------------------------------------
    # Structured fields
    # ---------------------------------------------------------
    keywords: Tuple[str, ...] = field(default_factory=tuple)

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> "Category":

        validated = validate_entity_fields(
            cls,
            data,
            required_fields={"id", "name", "level"},
            to_remove={"semantic_hash"},
        )

        cls._validate(validated)

        semantic_hash = SemanticHash.from_text(
            cls._build_embedding_text(
                name=validated["name"],
                description=validated.get("description", ""),
                keywords=validated.get("keywords", ()),
            )
        ).value

        return cls(**validated, semantic_hash=semantic_hash)

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------
    @staticmethod
    def _validate(data: dict[str, Any]) -> None:

        if not data.get("id"):
            raise CategoryNameError("Category ID cannot be empty.")

        if not data.get("name"):
            raise CategoryNameError("Category name cannot be empty.")

        level = data.get("level")
        if not isinstance(level, int) or level < 1:
            raise CategoryNameError(
                "Category level must be a positive integer."
            )

        if len(data["name"]) > 100:
            raise CategoryNameError(
                "Category name cannot exceed 100 characters."
            )

        if data.get("parent_id") == data.get("id"):
            raise CategoryNameError(
                "Category cannot reference itself as parent."
            )

    # ---------------------------------------------------------
    # Embedding text builder
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Public behavior
    # ---------------------------------------------------------
    def to_embedding_text(self) -> str:
        return self._build_embedding_text(
            self.name,
            self.description or "",
            self.keywords or (),
        )


    def with_id(self, new_id: str) -> Category:
        return replace(self, id=normalize_str(new_id))


    def to_dict(self) -> dict:
        return asdict(self)


if __name__ == "__main__":

    category = Category.create(
        id="1",
        name="Electronics",
        level=1,
        parent_id=None,
        description="All electronic items",
        keywords=("electronics", "gadgets"),
        gender="unisex",
        direction="kids",
        brand=None,
        is_leaf=False
    )

    print(category)