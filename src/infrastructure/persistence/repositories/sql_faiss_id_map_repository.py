# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.faiss_id_mapper import FaissIdMapper


class SQLFaissIdMapperRepository(FaissIdMapper):

    def __init__(self, db: Session):
        self.db = db


    def get_or_create_faiss_id(self, entity_uuid: UUID) -> int:
        # 1) Buscar si ya existe
        row = (
            self.db.execute(
                text(
                    """
                    SELECT faiss_id
                    FROM faiss_id_map
                    WHERE entity_uuid = :entity_uuid
                    """
                ),
                {"entity_uuid": str(entity_uuid)},
            )
            .mappings()
            .first()
        )

        if row is not None:
            return int(row["faiss_id"])

        # 2) Insertar y dejar que SQLite asigne faiss_id (AUTOINCREMENT)
        self.db.execute(
            text(
                """
                INSERT INTO faiss_id_map (entity_uuid)
                VALUES (:entity_uuid)
                """
            ),
            {"entity_uuid": str(entity_uuid)},
        )
        self.db.commit()

        # 3) Recuperar el id asignado
        row2 = (
            self.db.execute(
                text(
                    """
                    SELECT faiss_id
                    FROM faiss_id_map
                    WHERE entity_uuid = :entity_uuid
                    """
                ),
                {"entity_uuid": str(entity_uuid)},
            )
            .mappings()
            .first()
        )

        if row2 is None:
            raise RuntimeError("Failed to create faiss_id mapping")

        return int(row2["faiss_id"])


    def get_uuid(self, faiss_id: int) -> UUID | None:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT entity_uuid
                    FROM faiss_id_map
                    WHERE faiss_id = :faiss_id
                    """
                ),
                {"faiss_id": int(faiss_id)},
            )
            .mappings()
            .first()
        )

        if row is None:
            return None

        return UUID(row["entity_uuid"])
