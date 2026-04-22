# -----------------------------------------------------------------
# Domain Events — Category
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class CategoryCreatedEvent(DomainEvent):
    """Emitted when a new category is created."""
    category_id: str = ""
    name: str = ""
    level: int = 0
    parent_id: str | None = None


@dataclass(frozen=True)
class CategoryKeywordsEnhancedEvent(DomainEvent):
    """Emitted when a category's keywords are enhanced from parents."""
    category_id: str = ""
    original_keyword_count: int = 0
    enhanced_keyword_count: int = 0


@dataclass(frozen=True)
class CategoryProfileCreatedEvent(DomainEvent):
    """Emitted when a category profile is created or updated."""
    category_id: str = ""
    gender: str | None = None
    direction: str | None = None
    business: str | None = None
    brand: str | None = None
    is_leaf: bool | None = None
