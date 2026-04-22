# -----------------------------------------------------------------
# Application Port — Event Bus (Interface)
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Type

from shared.kernel.domain_event import DomainEvent


class EventBus(ABC):
    """
    Port for an in-process event bus.

    Responsibilities:
      - Register handlers for specific event types
      - Publish events and dispatch them to all matching handlers
      - Log every event that flows through the bus
    """

    @abstractmethod
    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Register a handler for a specific event type."""
        raise NotImplementedError

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Dispatch an event to all registered handlers."""
        raise NotImplementedError

    @abstractmethod
    def publish_all(self, events: List[DomainEvent]) -> None:
        """Dispatch a list of events in order."""
        raise NotImplementedError
