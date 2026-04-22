from __future__ import annotations
from typing import List

from shared.kernel.domain_event import DomainEvent


class AggregateRoot:
    """
    Base class for all aggregate roots.

    Responsibilities:
      - Maintain an internal list of domain events
      - Provide _record_event() for subclasses
      - Provide pull_events() for the Unit of Work

    Rules:
      - Only aggregates may emit events
      - Entities MUST NOT emit events directly
    """

    def __init__(self) -> None:
        self._domain_events: List[DomainEvent] = []


    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)


    def pull_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
