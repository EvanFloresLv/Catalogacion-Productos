# ---------------------------------------------------------------------
# Business normalization helpers.
#
# The codebase mixes two conventions for the BLP (Brand Landing Page)
# business:
#
#   - DB / brand table:   "blp_liverpool", "blp_suburbia"
#   - Product / category: "liverpool-blp", "suburbia-blp"
#
# Centralizing the conversion here removes three duplicated
# implementations and makes adding a new business a single-line change.
# ---------------------------------------------------------------------
from __future__ import annotations

from typing import Iterable, Set


def normalize_brand_business(business: str) -> str:
    """``blp_liverpool`` → ``liverpool-blp``. Idempotent."""
    if not business:
        return business
    if business.startswith("blp_"):
        return f"{business[4:]}-blp"
    return business


def normalize_brand_businesses(businesses: Iterable[str]) -> Set[str]:
    """Vectorized form of :func:`normalize_brand_business`."""
    return {normalize_brand_business(b) for b in businesses if b}


def intersect_businesses(
    product_businesses: Iterable[str],
    brand_businesses: Iterable[str],
) -> Set[str]:
    """
    Compute the intersection of product.business and brand.business
    using the canonical ``X-blp`` representation on both sides.

    Returns the brand-filtered set when there is a non-empty
    intersection; otherwise returns the original product set so the
    caller can fall back to product_type-restricted search.
    """
    product_set = {b for b in product_businesses if b}
    brand_norm = normalize_brand_businesses(brand_businesses)

    if not brand_norm:
        return product_set

    intersection = product_set & brand_norm
    return intersection if intersection else product_set
