# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class SQLiteFaissIdMapper:

    def __init__(self, conn):
        self.conn = conn


    def get_or_create_faiss_id(self, entity_uuid: UUID) -> int:

        row = self.conn.execute(
            "SELECT faiss_id FROM faiss_id_map WHERE entity_uuid = ?",
            (str(entity_uuid),),
        ).fetchone()

        if row is not None:
            return int(row["faiss_id"])

        # Generar nuevo ID incremental estable
        row2 = self.conn.execute("SELECT COALESCE(MAX(faiss_id), 0) + 1 AS next_id FROM faiss_id_map").fetchone()
        next_id = int(row2["next_id"])

        self.conn.execute(
            "INSERT INTO faiss_id_map (faiss_id, entity_uuid) VALUES (?, ?)",
            (next_id, str(entity_uuid)),
        )
        self.conn.commit()
        return next_id


    def get_uuid(self, faiss_id: int) -> UUID | None:
        row = self.conn.execute(
            "SELECT entity_uuid FROM faiss_id_map WHERE faiss_id = ?",
            (int(faiss_id),),
        ).fetchone()

        if row is None:
            return None

        return UUID(row["entity_uuid"])
