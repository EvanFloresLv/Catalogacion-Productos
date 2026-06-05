# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import json
import logging
from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from llm_sdk.sync_sdk import LLM
from llm_sdk.domain.chat import ChatMessage, ChatPart

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from utils.prompt import Prompt
from infrastructure.llm.sdk_factory import get_llm_sdk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 50
MAX_RETRIES = 2
MAX_WORKERS = 4

# Re-ranking MUST be deterministic. We default to the re-ranker
# settings, but allow per-call override via the constructor.
DEFAULT_RERANK_TEMPERATURE = 0.7
DEFAULT_RERANK_MAX_TOKENS = None  # Let the model decide how many tokens it needs to output the ranked list.

# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class EnhanceClassificationCommand:
    data: list[dict[str, Any]]
    prompt_path: str = "./src/prompts/select_category.yaml"
    batch_size: int = DEFAULT_BATCH_SIZE


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class EnhanceClassificationUseCase:
    """
    Sends product + candidate categories to an LLM to re-rank them.

    Returns a list of dicts with:
      - product_sku
      - business
      - relevant_categories (list of category_ids ordered by relevance, may be empty)
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        temperature: float = DEFAULT_RERANK_TEMPERATURE,
        max_tokens: int = DEFAULT_RERANK_MAX_TOKENS,
        sdk: LLM | None = None,
    ):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._sdk = sdk or get_llm_sdk()

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def execute(self, cmd: EnhanceClassificationCommand) -> list[dict[str, Any]]:
        if not cmd.data:
            logger.warning("No data to enhance.")
            return []

        prompt = Prompt(cmd.prompt_path)
        results = self._process_batches(cmd.data, prompt, cmd.batch_size)

        logger.info(f"Enhancement complete: {len(results)} results from {len(cmd.data)} products.")
        return results

    # -----------------------------------------------------------------
    # Batch processing
    # -----------------------------------------------------------------
    def _process_batches(
        self, data: list[dict], prompt: Prompt, batch_size: int
    ) -> list[dict[str, Any]]:

        batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
        total = len(batches)
        all_results: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._process_single_batch, batch, prompt): idx
                for idx, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    batch_results = future.result()
                    if batch_results:
                        all_results.extend(batch_results)
                        logger.info(f"Batch {idx + 1}/{total}: {len(batch_results)} results.")
                    else:
                        logger.warning(f"Batch {idx + 1}/{total}: no results.")
                except Exception as e:
                    logger.error(f"Batch {idx + 1}/{total} failed: {e}")

        return all_results

    def _process_single_batch(
        self, batch: list[dict], prompt: Prompt
    ) -> list[dict[str, Any]] | None:

        prompt_data = prompt.get_prompt(input_data=json.dumps(batch, ensure_ascii=False))
        system = str(prompt_data.get("system", ""))
        user = str(prompt_data.get("user", ""))
        schema = prompt_data.get("schema")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._sdk.chat(
                    messages=[
                        ("model", system),
                        ("user", user),
                    ],
                    output_schema=schema,
                    output_mime_type="application/json",
                    provider="gemini",
                    model=self._model,
                    # Deterministic re-ranking.
                    temperature=self._temperature,
                    max_output_tokens=self._max_tokens,
                )
                result = json.loads(resp.content)
                return result if isinstance(result, list) else [result]

            except Exception as e:
                logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")

        logger.error("All retries exhausted for batch.")
        return None
