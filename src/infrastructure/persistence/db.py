# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


def create_sqlite_engine(db_path: str):

    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        future=True
    )

    return engine


def create_session_factory(engine):

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    return Session