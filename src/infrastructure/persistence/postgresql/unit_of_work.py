# -----------------------------------------------------------------
# Infrastructure — SQLAlchemy Unit of Work
# -----------------------------------------------------------------
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from shared.kernel.domain_event import DomainEvent
from shared.kernel.unit_of_work import UnitOfWork
from application.ports.outbox_writer import OutboxWriter
from application.event_handlers.base import EventHandler


class SqlAlchemyUnitOfWork(UnitOfWork):
    """
    Concrete Unit of Work backed by SQLAlchemy.

    commit() flow:
      1. Pull events from all tracked aggregates
      2. Persist events to outbox (same transaction)
      3. Dispatch events to in-process handlers
      4. Commit the database transaction
      5. Clear tracked aggregates

    rollback() flow:
      1. Rollback the database transaction
      2. Clear tracked aggregates
    """

    def __init__(
        self,
        session: Session,
        outbox: OutboxWriter,
        event_handlers: List[EventHandler] | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._outbox = outbox
        self._event_handlers = event_handlers or []

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def session(self) -> Session:
        return self._session

    # ---------------------------
    # Lifecycle
    # ---------------------------
    def commit(self) -> None:
        """
        1. Pull events from tracked aggregates
        2. Persist to outbox
        3. Dispatch to handlers
        4. DB commit
        """
        try:
            # Collect all events
            all_events: List[DomainEvent] = []
            for aggregate in self._tracked:
                all_events.extend(aggregate.pull_events())

            # Persist to outbox (same transaction)
            if all_events:
                self._outbox.write(all_events)

            # Commit the database transaction
            self._session.commit()

            # Dispatch events to in-process handlers (after commit)
            for event in all_events:
                for handler in self._event_handlers:
                    try:
                        handler.handle(event)
                    except Exception as e:
                        # Handlers MUST NOT break the main flow
                        print(f"[EventHandler Error] {handler.__class__.__name__}: {e}")

            # Clean up
            self._tracked.clear()
        except Exception as e:
            self._session.rollback()
            self._tracked.clear()
            print(f"[Transaction Error] {e}")

    def rollback(self) -> None:
        self._session.rollback()
        self._tracked.clear()
