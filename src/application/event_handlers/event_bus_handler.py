# -----------------------------------------------------------------
# Application — Event Handler — Event Bus Bridge
# -----------------------------------------------------------------
"""
Bridges the existing EventHandler interface used by the UoW
with the new EventBus infrastructure.

This handler simply forwards every event to the event bus,
which then dispatches to all registered projection handlers.
"""
from __future__ import annotations

from shared.kernel.domain_event import DomainEvent
from application.event_handlers.base import EventHandler
from application.ports.event_bus import EventBus


class EventBusHandler(EventHandler):
    """
    Forwards domain events from the Unit of Work to the Event Bus.

    Usage:
      bus = InProcessEventBus()
      wire_projections(bus, session_factory)
      handler = EventBusHandler(bus)
      uow = SqlAlchemyUnitOfWork(session, [handler])
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def handle(self, event: DomainEvent) -> None:
        self._bus.publish(event)
