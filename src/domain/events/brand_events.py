# -----------------------------------------------------------------
# Domain Events — Brand
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class BrandCreatedEvent(DomainEvent):
    name: str = ""
    business: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BrandUpdatedEvent(DomainEvent):
    name: str = ""
    business: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BrandDeletedEvent(DomainEvent):
    name: str = ""