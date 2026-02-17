# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class FaissIdMapper(ABC):

    @abstractmethod
    def get_or_create_faiss_id(self, entity_uuid: UUID) -> int:
        raise NotImplementedError


    @abstractmethod
    def get_uuid(self, faiss_id: int) -> UUID | None:
        raise NotImplementedError