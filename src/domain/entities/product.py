# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Any, Iterable

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import ProductError
from utils.domain_validatons import (
    validate_entity_fields,
    normalize_text,
    normalize_iterable,
)

# -------------------------------------------------------------
# Constants / Domain Rules
# -------------------------------------------------------------
VALID_PRODUCT_TYPES: dict[str, Tuple[str, ...]] = {
    "marketplace": ("liverpool", "suburbia"),
    "marcas propias": ("liverpool",),
    "sfera": ("liverpool", "suburbia"),
    "regular": ("liverpool",),
    "suburbia": ("suburbia",),
    "internet": ("liverpool",),
}

# -------------------------------------------------------------
# Entity
# -------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Product:
    """
    Product entity (immutable, normalized, deterministic).

    Rules:
    - product_type defines business automatically
    - keywords are always normalized and deduplicated
    - no mutable structures (ACID-safe in memory)
    """

    # Required
    name: str
    sku: str
    description: str
    brand: str
    direction: str
    product_type: str

    # Derived / controlled
    business: Tuple[str, ...]

    # Optional
    keywords: Tuple[str, ...] = field(default_factory=tuple)
    gender: str | None = None

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> Product:
        """
        Factory with:
        - strict validation
        - normalization
        - deterministic keyword extraction
        - controlled derived fields
        """

        validated = validate_entity_fields(
            cls,
            data,
            required_fields={"name", "sku", "description", "brand", "direction", "product_type"},
            to_remove={"business", "keywords"},
        )

        # -----------------------------------------------------
        # Validate product_type
        # -----------------------------------------------------
        product_type = validated.get("product_type", "")

        if product_type and product_type not in VALID_PRODUCT_TYPES:
            raise ProductError(
                f"Invalid product_type '{product_type}'. "
                f"Allowed: {', '.join(sorted(VALID_PRODUCT_TYPES))}"
            )

        # -----------------------------------------------------
        # Derive business (no external override)
        # -----------------------------------------------------
        business = VALID_PRODUCT_TYPES.get(product_type, ())

        # -----------------------------------------------------
        # Keyword extraction (deterministic)
        # -----------------------------------------------------
        keywords = cls._extract_keywords(
            name=validated.get("name"),
            description=validated.get("description"),
            explicit=data.get("keywords"),
        )

        return cls(
            **validated,
            business=business,
            keywords=keywords,
        )

    # ---------------------------------------------------------
    # Keyword extraction (pure function)
    # ---------------------------------------------------------
    @staticmethod
    def _extract_keywords(
        name: str,
        description: str,
        explicit: Iterable[str] | None,
    ) -> Tuple[str, ...]:

        tokens: set[str] = set()

        # From text fields
        for text in (name, description):
            if not text:
                continue

            for word in text.split():
                normalized = normalize_text(word)
                if normalized:
                    tokens.add(normalized.lower())

        # Explicit keywords
        if explicit:
            tokens.update(normalize_iterable(explicit))

        return tuple(sorted(tokens))

    # ---------------------------------------------------------
    # Embedding text
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

    def to_embedding_text(self) -> str:
        return self._build_embedding_text(
            name=self.name,
            description=self.description or "",
            keywords=self.keywords,
        )

if __name__ == "__main__":

    product = Product.create(
        name="Example Product",
        sku="EX-123",
        description="This is an example product.",
        brand="Example Brand",
        direction="Example Direction",
        keywords=["example", "product", "test"],
        product_type="marketplace",
    )

    print(product)