# -----------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import UUID

# ── Entities ─────────────────────────────────────────────────────
from domain.entities.category import Category
from domain.entities.product import Product
from domain.entities.brand import Brand
from domain.entities.embedding import Embedding
from domain.entities.result import (
    CategoryMatch,
    ClassificationResult,
)

# ── Value Objects ────────────────────────────────────────────────
from domain.value_objects.semantic_hash import SemanticHash

# ── Aggregates ───────────────────────────────────────────────────
from domain.aggregates.category_catalog import CategoryCatalog
from domain.aggregates.product_classification_catalog import ProductClassification

# ── Domain Events ────────────────────────────────────────────────
from domain.events.category_events import (
    CategoryCreatedEvent,
    CategoryKeywordsEnhancedEvent,
)
from domain.events.product_events import (
    ProductCreatedEvent,
    ProductClassifiedEvent,
)
from domain.events.embedding_events import EmbeddingGeneratedEvent


# =================================================================
#  Domain Factory
# =================================================================
class DomainFactory:
    """
    Static factory methods for every domain object.
    """

    # =============================================================
    #  ENTITIES
    # =============================================================

    # ── Brand ────────────────────────────────────────────────────
    @staticmethod
    def create_brand(
        name: str,
        business: str
    ) -> Brand:
        """Create a Brand entity via its own ``create()`` factory."""
        return Brand.create(
            name=name,
            business=business
        )


    # ── Category ─────────────────────────────────────────────────
    @staticmethod
    def create_category(
        *,
        id: str,
        name: str,
        level: int,
        parent_id: str | None = None,
        description: str | None = None,
        keywords: Tuple[str, ...] | List[str] | None = None,
        gender: str | None = None,
        direction: str | None = None,
        brand: Brand | None = None,
        is_leaf: bool | None = None,
        group_articles: List[str] | None = None,
    ) -> Category:
        """
        Create a Category entity via its own ``create()`` factory.

        The semantic hash is computed internally from name + description
        + keywords.
        """
        return Category.create(
            id=id,
            name=name,
            level=level,
            parent_id=parent_id,
            description=description,
            keywords=keywords,
            gender=gender,
            direction=direction,
            brand=brand,
            is_leaf=is_leaf,
            group_articles=group_articles,
        )

    # ── Product ──────────────────────────────────────────────────
    @staticmethod
    def create_product(
        *,
        sku: str,
        name: str,
        description: str,
        product_type: str,
        keywords: Tuple[str, ...] | List[str] | None = None,
        brand: str | None = None,
        direction: str | None = None,
        gender: str | None = None,
    ) -> Product:
        """
        Create a Product entity via its own ``create()`` factory.

        ``business`` is auto-derived from ``product_type`` when omitted.
        """
        data: Dict[str, Any] = dict(
            sku=sku,
            name=name,
            description=description,
            product_type=product_type,
        )

        if keywords is not None:
            data["keywords"] = keywords
        if brand is not None:
            data["brand"] = brand
        if direction is not None:
            data["direction"] = direction
        if gender is not None:
            data["gender"] = gender

        return Product.create(**data)

    # ── Embedding ────────────────────────────────────────────────
    @staticmethod
    def create_embedding(
        *,
        category_id: str,
        vector: Tuple[float, ...] | List[float],
        content_hash: str,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> Embedding:
        """Create an Embedding entity via its own ``create()`` factory."""
        data: Dict[str, Any] = dict(
            category_id=category_id,
            vector=vector,
            content_hash=content_hash,
        )
        if id is not None:
            data["id"] = id
        if created_at is not None:
            data["created_at"] = created_at
        return Embedding.create(**data)

    # ── Classification Results ───────────────────────────────────
    @staticmethod
    def create_category_match(
        *,
        category_id: str,
        score: float,
        path: str | None = None,
    ) -> CategoryMatch:
        """Create a CategoryMatch result."""
        return CategoryMatch(
            category_id=category_id,
            score=score,
            path=path,
        )

    @staticmethod
    def create_classification_result(
        *,
        product_sku: str,
        best: CategoryMatch,
        top_k: List[CategoryMatch],
    ) -> ClassificationResult:
        """Create a ClassificationResult from pre-built matches."""
        return ClassificationResult(
            product_sku=product_sku,
            best=best,
            top_k=top_k,
        )

    # =============================================================
    #  VALUE OBJECTS
    # =============================================================

    @staticmethod
    def create_semantic_hash(*, text: str) -> SemanticHash:
        """Create a SemanticHash from raw text."""
        return SemanticHash.from_text(text)

    # =============================================================
    #  AGGREGATES
    # =============================================================

    @staticmethod
    def create_category_catalog() -> CategoryCatalog:
        """Create a fresh CategoryCatalog aggregate."""
        return CategoryCatalog()

    @staticmethod
    def create_product_classification(
        *, product: Product,
    ) -> ProductClassification:
        """Create a ProductClassification aggregate for a given product."""
        return ProductClassification(product=product)

    # =============================================================
    #  DOMAIN EVENTS
    # =============================================================

    @staticmethod
    def create_category_created_event(
        *,
        category_id: str,
        name: str,
        level: int,
        parent_id: str | None = None,
    ) -> CategoryCreatedEvent:
        """Create a CategoryCreatedEvent."""
        return CategoryCreatedEvent(
            category_id=category_id,
            name=name,
            level=level,
            parent_id=parent_id,
        )

    @staticmethod
    def create_category_keywords_enhanced_event(
        *,
        category_id: str,
        original_keyword_count: int,
        enhanced_keyword_count: int,
    ) -> CategoryKeywordsEnhancedEvent:
        """Create a CategoryKeywordsEnhancedEvent."""
        return CategoryKeywordsEnhancedEvent(
            category_id=category_id,
            original_keyword_count=original_keyword_count,
            enhanced_keyword_count=enhanced_keyword_count,
        )

    @staticmethod
    def create_product_created_event(
        *,
        sku: str,
        name: str,
        product_type: str,
        business: List[str] | None = None,
    ) -> ProductCreatedEvent:
        """Create a ProductCreatedEvent."""
        return ProductCreatedEvent(
            sku=sku,
            name=name,
            product_type=product_type,
            business=business,
        )

    @staticmethod
    def create_product_classified_event(
        *,
        sku: str,
        business: str,
        best_category_id: str,
        best_score: float,
        top_k_count: int,
    ) -> ProductClassifiedEvent:
        """Create a ProductClassifiedEvent."""
        return ProductClassifiedEvent(
            sku=sku,
            business=business,
            best_category_id=best_category_id,
            best_score=best_score,
            top_k_count=top_k_count,
        )

    @staticmethod
    def create_embedding_generated_event(
        *,
        category_id: str,
        dimension: int,
        content_hash: str,
    ) -> EmbeddingGeneratedEvent:
        """Create an EmbeddingGeneratedEvent."""
        return EmbeddingGeneratedEvent(
            category_id=category_id,
            dimension=dimension,
            content_hash=content_hash,
        )