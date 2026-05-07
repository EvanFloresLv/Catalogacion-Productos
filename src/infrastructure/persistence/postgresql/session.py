# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ----------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from config.settings import settings

engine = create_engine(settings.database_url, echo=False)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=engine
)