# -----------------------------------------------------------------
# Infrastructure ORM — Outbox Model
# -----------------------------------------------------------------
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.postgresql.base import Base


class OutboxModel(Base):
    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    event_type: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
    )

    occurred_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    processed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )