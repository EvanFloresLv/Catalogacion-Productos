# -----------------------------------------------------------------
# Application Port — Outbox Writer (Interface)
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from shared.kernel.domain_event import DomainEvent


class OutboxWriter(ABC):
    """
    Port for persisting domain events into the outbox table.

    Rules:
      - Must be called WITHIN the same DB transaction as the aggregate mutation
      - The UnitOfWork orchestrates this
    """

    @abstractmethod
    def write(self, events: List[DomainEvent]) -> None:
        """Persist events to the outbox table."""
        raise NotImplementedError
