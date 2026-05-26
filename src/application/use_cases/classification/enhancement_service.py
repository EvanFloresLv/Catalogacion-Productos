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


class EnhancementService:

    def enhance(self, results: dict, product_data: dict) -> dict:

        payload = self._build_payload(results, product_data)

        enhance_use_case = EnhanceClassificationUseCase()

        response = enhance_use_case.execute(
            EnhanceClassificationCommand(data=payload)
        )

        enhanced = {}

        for item in response:

            sku = item.get("product_sku")
            business = item.get("business")

            relevant_ids = item.get("relevant_categories", [])

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

                for match in classification.top_k:

                    path = (
                        match.path
                        if "blp" not in business
                        else " > ".join(match.path.split(" > ")[1:])
                    )

                    candidates.append({
                        "id": match.category_id,
                        "name": match.name,
                        "path": path,
                    })

                payload.append({
                    "product_sku": product.sku,
                    "product_name": product.name,
                    "business": business,
                    "candidates": candidates,
                })

        return payload