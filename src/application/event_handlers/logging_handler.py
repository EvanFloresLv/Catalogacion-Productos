# -----------------------------------------------------------------
# Application — Event Handler — Logging
# -----------------------------------------------------------------
from __future__ import annotations

import logging

from shared.kernel.domain_event import DomainEvent
from application.event_handlers.base import EventHandler

logger = logging.getLogger(__name__)


class LoggingEventHandler(EventHandler):
    """
    Logs all domain events.
    Serves as a template for future message-bus integration.
    """

    def handle(self, event: DomainEvent) -> None:
        logger.info(
            "[DomainEvent] %s | id=%s | occurred_on=%s | payload=%s",
            event.event_type,
            event.event_id,
            event.occurred_on,
            event.to_dict(),
        )
