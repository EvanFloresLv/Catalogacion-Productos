# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
import infrastructure.persistence.postgresql.models

from infrastructure.persistence.postgresql.base import Base
from infrastructure.persistence.postgresql.session import engine


def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully.")


if __name__ == "__main__":
    reset_database()