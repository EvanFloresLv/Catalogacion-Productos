# -----------------------------------------------------------------
# Shared Kernel — Domain Event
# -----------------------------------------------------------------
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class DomainEvent:
    """
    Base class for all domain events.

    Rules:
      - Immutable (frozen dataclass)
      - Serializable via to_dict()
      - event_id and occurred_on are auto-generated
      - No infrastructure dependencies
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_on: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def event_type(self) -> str:
        """Fully qualified class name used as the event type key."""
        return f"{self.__class__.__module__}.{self.__class__.__qualname__}"
