from sqlalchemy import text
import infrastructure.persistence.postgresql.models

from infrastructure.persistence.postgresql.base import Base
from infrastructure.persistence.postgresql.session import engine


def reset_database():
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)

        # Vector extension before create tables (PostgreSQL won't know about it otherwise)
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=conn)

    print("Tables dropped and recreated successfully.")


if __name__ == "__main__":
    reset_database()