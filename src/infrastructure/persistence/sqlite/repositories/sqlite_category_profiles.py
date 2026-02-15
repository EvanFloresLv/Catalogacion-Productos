# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

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

    arr = json.loads(s)

    return set(arr)


def _set_to_json(s: set[str] | None) -> str | None:

    if s is None:
        return None

    return json.dumps(sorted(list(s)))


class SQLiteCategoryProfileRepository(CategoryProfileRepository):

    def __init__(self, conn):
        self.conn = conn


    def upsert_profile(
        self,
        category_id: UUID,
        keywords: list[str],
        allowed_genders: set[str] | None,
        allowed_business_types: set[str] | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO category_profiles
            (category_id, keywords_json, allowed_genders_json, allowed_business_types_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(category_id),
                json.dumps([k.strip() for k in keywords if k.strip()]),
                _set_to_json(allowed_genders),
                _set_to_json(allowed_business_types),
            ),
        )
        self.conn.commit()


    def list_all_profiles(self) -> list[CategoryProfile]:
        rows = self.conn.execute(
            """
            SELECT
              c.id as category_id,
              c.name as category_name,
              c.parent_id as parent_id,
              p.keywords_json as keywords_json,
              p.allowed_genders_json as allowed_genders_json,
              p.allowed_business_types_json as allowed_business_types_json
            FROM categories c
            JOIN category_profiles p ON p.category_id = c.id
            """
        ).fetchall()

        out: list[CategoryProfile] = []

        for r in rows:
            parent = r["parent_id"]

            category = Category(
                id=UUID(r["category_id"]),
                name=r["category_name"],
                parent_id=UUID(parent) if parent else None,
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
