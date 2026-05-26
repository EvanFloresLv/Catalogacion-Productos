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
from llm_sdk.providers.sync_registry import ProviderSpec
from llm_sdk_provider_gemini import SyncGeminiClient
from llm_sdk.domain.chat import ChatMessage, ChatPart

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from utils.prompt import Prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 50
MAX_RETRIES = 2
MAX_WORKERS = 4

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
    Sends product + candidate categories to an LLM to filter relevant ones.

    Returns a list of dicts with:
      - product_sku
      - business
      - relevant_categories (list of category_ids ordered by relevance, may be empty)
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self._model = model
        self._sdk = self._init_sdk()

    def _init_sdk(self) -> LLM:
        sdk = LLM.default()
        sdk.registry.register(ProviderSpec(
            name="gemini",
            factory=lambda: SyncGeminiClient(location=sdk.settings.gemini.location),
            models={self._model},
        ))
        return sdk

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
                        ChatMessage(role="model", parts=[ChatPart(type="text", text=system)]),
                        ChatMessage(role="user", parts=[ChatPart(type="text", text=user)]),
                    ],
                    output_schema=schema,
                    provider="gemini",
                    model=self._model,
                )
                result = json.loads(resp.content)
                return result if isinstance(result, list) else [result]

            except Exception as e:
                logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")

        logger.error("All retries exhausted for batch.")
        return None
