# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# ----------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    poolclass=QueuePool,
    pool_size=8,           # Sustained concurrent connections
    max_overflow=5,        # Burst up to 13 total (under Supabase pooler limit of 15)
    pool_pre_ping=True,    # Detect stale connections (critical for remote DBs)
    pool_recycle=1800,     # Recycle connections every 30 minutes
    pool_timeout=30,       # Wait up to 30s for a connection from the pool
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=engine
)