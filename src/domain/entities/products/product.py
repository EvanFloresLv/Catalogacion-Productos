# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, fields
from typing import Tuple, Any, Iterable

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import ProductError


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _normalize_text(value: str | None) -> str | None:
    """
    Normalizes text by:
    - Converting unicode to NFKD form
    - Removing numbers and symbols (keeping only letters and spaces)
    - Collapsing multiple whitespace to single space
    - Stripping leading/trailing whitespace
    """
    if value is None:
        return None

    value = unicodedata.normalize("NFKD", str(value))
    # Remove numbers and symbols, keep only letters and spaces
    value = re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()

    return value if value else None


def _normalize_keywords(values: Iterable[str] | None) -> Tuple[str, ...]:
    """
    Normalizes keywords by:
    - Keeping only alphabetic words (removes numbers, symbols, punctuation)
    - Removing duplicates
    - Normalizing unicode and whitespace
    - Converting to lowercase
    - Sorting alphabetically
    """
    if not values:
        return ()

    normalized = set()
    for v in values:
        if isinstance(v, str) and v.strip():
            normalized_text = _normalize_text(v)
            if normalized_text:
                # Keep only alphabetic characters (words)
                if normalized_text.isalpha():
                    normalized.add(normalized_text.lower())

    return tuple(sorted(normalized)) if normalized else ()


@dataclass(frozen=True)
class Product:
    """
    Product entity with normalized data.

    Valid product types:
    - marketplace
    - marcas propias
    - sfera
    - regular
    - suburbia
    - internet
    """
    # Required fields
    name: str
    business: str
    sku: str
    description: str
    keywords: Tuple[str, ...]
    product_type: str

    # Optional fields
    gender: str | None = None
    direction: str | None = None
    brand: str | None = None

    @classmethod
    def create(cls, **data) -> Product:
        """
        Flexible factory for creating Product instances with automatic normalization.

        Features:
        - Auto-maps dataclass fields
        - Rejects unknown fields
        - Normalizes all text (unicode NFKD, whitespace collapse, strip)
        - Normalizes keywords (deduplicate, lowercase, sort)
        - Validates product_type against allowed values

        Args:
            **data: Field values for the product

        Returns:
            Product: Normalized product instance

        Raises:
            ProductError: If unknown fields provided or validation fails
        """
        VALID_PRODUCT_TYPES = {
            "marketplace",
            "marcas propias",
            "sfera",
            "regular",
            "suburbia",
            "internet"
        }

        field_names = {f.name for f in fields(cls)}
        allowed_input_fields = field_names

        # -----------------------------
        # Guard against unknown fields
        # -----------------------------
        unknown = set(data.keys()) - allowed_input_fields
        if unknown:
            raise ProductError(
                f"Unknown fields for Product: {unknown}"
            )

        normalized: dict[str, Any] = {}

        # Extract and accumulate keywords
        accumulated_keywords = set()

        # First pass: extract keywords from text fields
        for field_name in ["name", "description"]:
            value = data.get(field_name)
            if value and isinstance(value, str):
                words = value.split()
                for word in words:
                    normalized_word = _normalize_text(word)
                    if normalized_word:
                        accumulated_keywords.add(normalized_word.lower())

        # Add explicit keywords if provided
        explicit_keywords = data.get("keywords")
        if explicit_keywords:
            normalized_kw = _normalize_keywords(explicit_keywords)
            accumulated_keywords.update(normalized_kw)

        # Second pass: normalize all fields
        for field_name in allowed_input_fields:
            value = data.get(field_name)

            if value is None:
                continue

            # Handle keywords separately
            if field_name == "keywords":
                normalized[field_name] = tuple(sorted(accumulated_keywords))

            # Special handling for sku - preserve original (no symbol removal)
            elif field_name == "sku":
                sku_value = str(value).strip()
                if sku_value:
                    normalized[field_name] = sku_value

            # Normalize text fields
            elif isinstance(value, str):
                normalized_value = _normalize_text(value)
                if normalized_value:
                    # Keep original case for name and description
                    if field_name in ["name", "description"]:
                        normalized[field_name] = normalized_value
                    # Lowercase for other string fields
                    else:
                        normalized[field_name] = normalized_value.lower()

            # Pass through non-string values
            else:
                normalized[field_name] = value

        # Validate product_type if provided
        if "product_type" in normalized:
            product_type = normalized["product_type"]
            if product_type and product_type not in VALID_PRODUCT_TYPES:
                raise ProductError(
                    f"Invalid product_type '{product_type}'. "
                    f"Must be one of: {', '.join(sorted(VALID_PRODUCT_TYPES))}"
                )

        # Ensure keywords is set even if empty
        if "keywords" not in normalized:
            normalized["keywords"] = tuple(sorted(accumulated_keywords))

        # Validate required fields are present
        required_fields = {"name", "business", "sku", "description", "product_type", "keywords"}
        missing_fields = required_fields - set(normalized.keys())
        if missing_fields:
            raise ProductError(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )

        return cls(**normalized)

    @staticmethod
    def _build_embedding_text(
        name: str,
        description: str,
        keywords: Tuple[str, ...],
    ) -> str:
        """Build text representation for embedding generation."""
        return (
            f"TÍTULO: {name}\n"
            f"DESCRIPCIÓN: {description}\n"
            f"PALABRAS CLAVE: {', '.join(keywords)}"
        )

    def to_embedding_text(self) -> str:
        """
        Generate text representation suitable for embedding generation.

        Returns:
            str: Formatted text combining title, description, and keywords
        """
        return self._build_embedding_text(
            name=self.name,
            description=self.description or "",
            keywords=self.keywords
        )