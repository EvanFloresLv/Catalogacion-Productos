# -----------------------------------------------------------------
# Domain Events — Category
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class CategoryCreatedEvent(DomainEvent):
    category_id: str = ""
    name: str = ""
    level: int = 0
    parent_id: str | None = None


@dataclass(frozen=True)
class CategoryKeywordsEnhancedEvent(DomainEvent):
    category_id: str = ""
    original_keyword_count: int = 0
    enhanced_keyword_count: int = 0
