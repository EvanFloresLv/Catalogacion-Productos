# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import logging

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.result import ClassificationResult

from application.use_cases.classification.enhance_classification import (
    EnhanceClassificationCommand,
    EnhanceClassificationUseCase,
)

logger = logging.getLogger(__name__)


# Cap long descriptions to keep the LLM prompt small. 200 chars is
# plenty for disambiguation and avoids a 2 KB marketing blurb.
_MAX_DESC_CHARS = 200


def _truncate(text: str | None, limit: int) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class EnhancementService:

    def enhance(self, results: dict, product_data: dict) -> dict:

        payload = self._build_payload(results, product_data)

        enhance_use_case = EnhanceClassificationUseCase()

        response = enhance_use_case.execute(
            EnhanceClassificationCommand(data=payload)
        )

        enhanced = {}

        for item in response:

            # Accept both the compact keys (sku/biz/rel) and the old
            # verbose keys (product_sku/business/relevant_categories).
            sku = item.get("sku") or item.get("product_sku")
            business = item.get("biz") or item.get("business")
            relevant_ids = (
                item.get("rel")
                if item.get("rel") is not None
                else item.get("relevant_categories", [])
            )

            original = results.get(sku, {}).get(business)

            if not original:
                continue

            # If LLM returned empty, skip enhancement and keep original result
            if not relevant_ids:
                logger.debug(
                    "No relevant categories for %s/%s, keeping original.",
                    sku,
                    business,
                )
                continue

            lookup = {
                match.category_id: match
                for match in original.top_k
            }

            reordered = [
                lookup[category_id]
                for category_id in relevant_ids
                if category_id in lookup
            ]

            if not reordered:
                logger.warning(
                    "LLM returned categories outside original top_k"
                )
                continue

            enhanced.setdefault(sku, {})[business] = ClassificationResult(
                product_sku=sku,
                best=reordered[0],
                top_k=reordered,
                query=original.query,
            )

        return enhanced

    def _build_payload(self, results, product_data):

        payload = []

        for sku, businesses in results.items():

            data = product_data.get(sku)

            if not data:
                continue

            product = data["product"]

            for business, classification in businesses.items():

                if not classification or not classification.top_k:
                    continue

                candidates = []

                # For BLP businesses, strip the first path level (the
                # brand) so the LLM sees only the catalog-side path.
                for match in classification.top_k:

                    if match.path is None:
                        path = match.name or ""
                    elif "blp" in business:
                        path = " > ".join(match.path.split(" > ")[1:])
                    else:
                        path = match.path

                    cand = {"id": match.category_id, "n": match.name, "p": path}
                    if match.keywords:
                        cand["k"] = list(match.keywords)
                    candidates.append(cand)

                item = {
                    "sku": product.sku,
                    "biz": business,
                    "n": product.name,
                    "b": product.brand,
                    "g": product.gender,
                    "t": sorted(product.article_group) if product.article_group else None,
                    "desc": _truncate(product.description, _MAX_DESC_CHARS),
                    "cands": candidates,
                }

                # Drop fields with no value to keep the prompt small.
                payload.append({k: v for k, v in item.items() if v not in (None, "", [])})

        return payload