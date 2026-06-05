# -----------------------------------------------------------------
# Infrastructure — SQLAlchemy Unit of Work
# -----------------------------------------------------------------
from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

from shared.kernel.domain_event import DomainEvent
from shared.kernel.unit_of_work import UnitOfWork
from application.event_handlers.base import EventHandler

logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """
    Concrete Unit of Work backed by SQLAlchemy.

    commit() flow:
      1. Pull events from all tracked aggregates
      2. Commit the database transaction
      3. Dispatch events to in-process handlers (post-commit)
      4. Clear tracked aggregates

    rollback() flow:
      1. Rollback the database transaction
      2. Clear tracked aggregates
    """

    def __init__(
        self,
        session: Session,
        event_handlers: List[EventHandler] | None = None,
    ) -> None:
        super().__init__()
        self._session = session
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
        2. Commit the database transaction
        3. Dispatch to handlers (post-commit, best-effort)
        """
        try:
            all_events: List[DomainEvent] = []
            for aggregate in self._tracked:
                all_events.extend(aggregate.pull_events())

            self._session.commit()

            for event in all_events:
                for handler in self._event_handlers:
                    try:
                        handler.handle(event)
                    except Exception as e:
                        # Handlers MUST NOT break the main flow
                        logger.exception(
                            "Event handler %s failed for %s: %s",
                            handler.__class__.__name__,
                            event.event_type,
                            e,
                        )

            self._tracked.clear()
        except Exception:
            self._session.rollback()
            self._tracked.clear()
            raise

    def rollback(self) -> None:
        self._session.rollback()
        self._tracked.clear()
