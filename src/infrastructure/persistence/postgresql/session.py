# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import logging

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# ----------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import settings

logger = logging.getLogger(__name__)

# HNSW recall knob. Postgres' default is 40, which favours latency
# over recall. For product-categorization (~100K embeddings) we
# want higher recall, so we set this once per connection.
# Override with the ``DB_HNSW_EF_SEARCH`` env var.
HNSW_EF_SEARCH = 64


def _on_connect(dbapi_connection, connection_record):
    """
    Run per-connection setup outside of any transaction.

    ``hnsw.ef_search`` is a session-scoped GUC, so it must be set
    without ``SET LOCAL`` (which would require an open transaction)
    and without polluting the application code that opens the
    session. Hooking the ``connect`` event runs the statement once
    when SQLAlchemy first acquires a connection from the pool, and
    the value persists for the lifetime of that pooled connection.
    """
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET hnsw.ef_search = {int(HNSW_EF_SEARCH)}")
            dbapi_connection.commit()
        finally:
            cursor.close()
    except Exception as e:
        # We don't want a connection-pool warmup failure to crash the
        # process; the GUC just won't be set on this connection and
        # we'll fall back to Postgres' default (ef_search=40).
        logger.warning(
            "Failed to set hnsw.ef_search=%s on new connection (%s); "
            "falling back to default recall",
            HNSW_EF_SEARCH,
            e,
        )


engine = create_engine(
    settings.database_url,
    echo=False,
    poolclass=QueuePool,
    pool_size=8,           # Sustained concurrent connections
    max_overflow=5,        # Burst up to 13 total (under Supabase pooler limit of 15)
    pool_pre_ping=True,    # Detect stale connections (critical for remote DBs)
    pool_recycle=1800,     # Recycle connections every 30 minutes
    pool_timeout=30,       # Wait up to 30s for a connection from the pool
    connect_args={"connect_timeout": 10},
)

# Per-connection HNSW tuning — runs once per pooled connection,
# outside any application transaction.
event.listen(engine, "connect", _on_connect)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=engine
)
