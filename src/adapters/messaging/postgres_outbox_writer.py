# -----------------------------------------------------------------
# Adapter — Outbox Writer (PostgreSQL implementation)
# -----------------------------------------------------------------
from __future__ import annotations

import json
from typing import List

from sqlalchemy.orm import Session

from shared.kernel.domain_event import DomainEvent
from application.ports.outbox_writer import OutboxWriter
from infrastructure.persistence.postgresql.models.outbox_model import OutboxModel


class PostgresOutboxWriter(OutboxWriter):
    """
    Persists domain events into the outbox table using SQLAlchemy.

    The session is shared with the Unit of Work so that events and
    aggregate mutations are committed in the SAME transaction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def write(self, events: List[DomainEvent]) -> None:
        for event in events:
            model = OutboxModel(
                event_type=event.event_type,
                event_id=event.event_id,
                occurred_on=event.occurred_on,
                payload=json.dumps(event.to_dict(), default=str),
                processed=False,
            )
            self._session.add(model)
