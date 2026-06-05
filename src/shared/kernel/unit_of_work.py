# -----------------------------------------------------------------
# Shared Kernel — Unit of Work (Interface)
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from shared.kernel.aggregate_root import AggregateRoot


class UnitOfWork(ABC):
    """
    Abstract Unit of Work.

    Responsibilities:
      - Track modified aggregates
      - On commit:
          1. Pull events from every tracked aggregate
          2. Dispatch events to in-process handlers
          3. Commit the DB transaction
      - On rollback: discard all changes

    Rules:
      - All write operations MUST go through UoW
    """

    def __init__(self) -> None:
        self._tracked: List[AggregateRoot] = []

    # ---------------------------
    # Tracking
    # ---------------------------
    def register(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate for event collection on commit."""
        if aggregate not in self._tracked:
            self._tracked.append(aggregate)

    # ---------------------------
    # Lifecycle
    # ---------------------------
    @abstractmethod
    def commit(self) -> None:
        """
        1. Pull events from tracked aggregates
        2. Dispatch events to handlers
        3. Commit the database transaction
        """
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Discard all pending changes and clear tracked aggregates."""
        raise NotImplementedError

    # ---------------------------
    # Context manager
    # ---------------------------
    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.rollback()
