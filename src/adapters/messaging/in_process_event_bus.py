# -----------------------------------------------------------------
# Infrastructure — In-Process Event Bus
# -----------------------------------------------------------------
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Type

from shared.kernel.domain_event import DomainEvent
from application.ports.event_bus import EventBus

logger = logging.getLogger(__name__)


class InProcessEventBus(EventBus):
    """
    Simple synchronous event bus that dispatches domain events
    to registered handlers.

    Features:
      - Logs every published event (type, id, timestamp)
      - Dispatches to all matching handlers
      - Catches handler exceptions so one failure doesn't block others
    """

    def __init__(self) -> None:
        self._handlers: Dict[
            Type[DomainEvent], List[Callable[[DomainEvent], None]]
        ] = defaultdict(list)

    # ---------------------------
    # Subscription
    # ---------------------------
    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        self._handlers[event_type].append(handler)
        logger.info(
            "[EventBus] Subscribed %s to %s",
            getattr(handler, "__qualname__", repr(handler)),
            event_type.__name__,
        )

    # ---------------------------
    # Publishing
    # ---------------------------
    def publish(self, event: DomainEvent) -> None:
        logger.info(
            "[EventBus] Publishing %s | id=%s | occurred_on=%s",
            event.event_type,
            event.event_id,
            event.occurred_on,
        )

        handlers = self._handlers.get(type(event), [])
        if not handlers:
            logger.debug(
                "[EventBus] No handlers registered for %s",
                event.event_type,
            )
            return

        for handler in handlers:
            handler_name = getattr(handler, "__qualname__", repr(handler))
            try:
                handler(event)
                logger.debug(
                    "[EventBus] ✓ %s handled %s",
                    handler_name,
                    event.event_type,
                )
            except Exception as exc:
                logger.error(
                    "[EventBus] ✗ %s failed on %s: %s",
                    handler_name,
                    event.event_type,
                    exc,
                    exc_info=True,
                )

    def publish_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            self.publish(event)
