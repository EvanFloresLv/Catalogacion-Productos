# -----------------------------------------------------------------
# Domain Events — Embedding
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

from shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class EmbeddingGeneratedEvent(DomainEvent):
    category_id: str = ""
    dimension: int = 0
    content_hash: str = ""
