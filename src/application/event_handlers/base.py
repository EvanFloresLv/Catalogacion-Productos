# -----------------------------------------------------------------
# Application — Event Handler (base)
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod

from shared.kernel.domain_event import DomainEvent


class EventHandler(ABC):
    """
    Base class for domain event handlers.

    Rules:
      - Do NOT modify aggregates inside handlers
      - Used for side effects: logging, notifications, etc.
      - Prepared for future async / messaging integration
    """

    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        raise NotImplementedError
