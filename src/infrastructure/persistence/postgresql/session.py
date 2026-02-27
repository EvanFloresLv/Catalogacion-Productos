# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------

DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/product_routing"

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)