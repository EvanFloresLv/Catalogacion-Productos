# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.category_profile_repository import CategoryProfileRepository
from application.ports.outbound.embedding_service import EmbeddingService
from application.ports.outbound.vector_index import VectorIndex


@dataclass(frozen=True)
class RebuildCategoryIndexCommand:
    pass


class RebuildCategoryIndexUseCase:
    def __init__(
        self,
        profiles: CategoryProfileRepository,
        embeddings: EmbeddingService,
        index: VectorIndex,
    ):
        self.profiles = profiles
        self.embeddings = embeddings
        self.index = index


    def execute(self, cmd: RebuildCategoryIndexCommand) -> dict:
        profiles = self.profiles.list_all_profiles()

        self.index.reset(self.embeddings.dimension())

        for prof in profiles:
            text = prof.category.name
            if prof.keywords:
                text += "\nkeywords: " + ", ".join(prof.keywords)

            vec = self.embeddings.embed_text(text)
            self.index.upsert(prof.category.id, vec)

        if hasattr(self.index, "save"):
            self.index.save()

        return {"indexed_categories": len(profiles)}