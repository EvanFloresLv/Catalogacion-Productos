# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.categories.category import Category
from domain.classification.category_constraints import CategoryConstraints
from domain.classification.category_profile import CategoryProfile
from application.ports.outbound.category_profile_repository import CategoryProfileRepository


def _json_to_set(s: str | None) -> set[str] | None:
    if s is None:
        return None
    return set(json.loads(s))


def _set_to_json(s: set[str] | None) -> str | None:
    if s is None:
        return None
    return json.dumps(sorted(list(s)))


class SQLCategoryProfileRepository(CategoryProfileRepository):

    def __init__(self, db: Session):
        self.db = db


    def upsert_profile(
        self,
        category_id: UUID,
        keywords: list[str],
        allowed_genders: set[str] | None,
        allowed_business_types: set[str] | None,
    ) -> None:
        clean_keywords = [k.strip() for k in keywords if k and k.strip()]

        self.db.execute(
            text(
                """
                INSERT INTO category_profiles
                    (category_id, keywords_json, allowed_genders_json, allowed_business_types_json)
                VALUES
                    (:category_id, :keywords_json, :allowed_genders_json, :allowed_business_types_json)
                ON CONFLICT(category_id) DO UPDATE SET
                    keywords_json = excluded.keywords_json,
                    allowed_genders_json = excluded.allowed_genders_json,
                    allowed_business_types_json = excluded.allowed_business_types_json
                """
            ),
            {
                "category_id": str(category_id),
                "keywords_json": json.dumps(clean_keywords),
                "allowed_genders_json": _set_to_json(allowed_genders),
                "allowed_business_types_json": _set_to_json(allowed_business_types),
            },
        )

        self.db.commit()


    def list_all_profiles(self) -> list[CategoryProfile]:
        rows = (
            self.db.execute(
                text(
                    """
                    SELECT
                        c.id AS category_id,
                        c.name AS category_name,
                        c.parent_id AS parent_id,
                        p.keywords_json AS keywords_json,
                        p.allowed_genders_json AS allowed_genders_json,
                        p.allowed_business_types_json AS allowed_business_types_json
                    FROM categories c
                    JOIN category_profiles p ON p.category_id = c.id
                    """
                )
            )
            .mappings()
            .all()
        )

        out: list[CategoryProfile] = []

        for r in rows:
            parent_id = r["parent_id"]

            category = Category(
                id=UUID(r["category_id"]),
                name=r["category_name"],
                parent_id=UUID(parent_id) if parent_id else None,
            )

            constraints = CategoryConstraints(
                allowed_genders=_json_to_set(r["allowed_genders_json"]),
                allowed_business_types=_json_to_set(r["allowed_business_types_json"]),
            )

            out.append(
                CategoryProfile(
                    category=category,
                    constraints=constraints,
                    keywords=json.loads(r["keywords_json"]),
                )
            )

        return out
