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
    "marketplace": ("liverpool", "suburbia", "liverpool-blp", "suburbia-blp"),
    "marcas propias": ("liverpool", "liverpool-blp"),
    "sfera": ("liverpool", "suburbia"),
    "regular": ("liverpool", "liverpool-blp"),
    "suburbia": ("suburbia", "suburbia-blp"),
    "catmex": ("suburbia", "suburbia-blp"),
    "internet": ("liverpool", "liverpool-blp"),
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
    sku: str
    name: str
    brand: str
    direction: str
    product_type: str

    # Derived / controlled
    business: Tuple[str, ...]

    # Optional
    keywords: Tuple[str, ...] = field(default_factory=tuple)
    category: str | None = None
    gender: str | None = None
    article_group: set[str] | None = None
    description: str | None = None

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
        # Validate product_type → resolve business
        # -----------------------------------------------------
        product_type = validated.pop("product_type")
        matched_key, business = cls._resolve_business(product_type)

        if not business:
            raise ProductError(
                f"Invalid product_type '{product_type}'. "
                f"Allowed: {', '.join(sorted(VALID_PRODUCT_TYPES))}"
            )

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
            product_type=matched_key,
            business=business,
            keywords=keywords,
        )

    # ---------------------------------------------------------
    # Business resolution (pure function)
    # ---------------------------------------------------------
    @staticmethod
    def _resolve_business(product_type: str) -> Tuple[str, Tuple[str, ...]]:
        """
        Resolve product_type to a canonical key and its business tuple.

        Strategy (priority order):
          1. Exact match (case-insensitive)
          2. Longest key contained in the input (avoids 'regular' matching 'irregular')

        Returns (matched_key, business) or ("", ()) if no match.
        """
        pt_lower = product_type.lower().strip()

        # 1. Exact match
        if pt_lower in VALID_PRODUCT_TYPES:
            return pt_lower, VALID_PRODUCT_TYPES[pt_lower]

        # 2. Longest-key substring match (most specific wins)
        candidates = [
            k for k in VALID_PRODUCT_TYPES
            if k in pt_lower
        ]

        if not candidates:
            return "", ()

        best = max(candidates, key=len)
        return best, VALID_PRODUCT_TYPES[best]

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
            if not text or str(text).lower() == "nan":
                continue

            for word in text.split():
                normalized = normalize_text(word)
                if normalized:
                    tokens.add(normalized.lower())

        # Explicit keywords
        if explicit:
            tokens.update(normalize_iterable(explicit))

        # Remove "nan" tokens
        tokens.discard("nan")

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

    def to_dict(self):
        return {
            "SKU": self.sku,
            "Product Name": self.name,
            "Description": self.description,
            "Keywords": self.keywords,
            "Category": self.category,
        }

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