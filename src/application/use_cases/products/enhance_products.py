# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
import logging
from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd

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
MAX_RETRIES = 3
WORKERS = 4

# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class EnhanceProductsCommand:
    data_file: str
    prompt_path: str = "./src/prompts/add_attributes.yml"
    batch_size: int = DEFAULT_BATCH_SIZE


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class EnhanceProductsUseCase:
    """
    Enhances product data using an LLM to generate additional attributes.

    Flow:
      1. Read products from Excel
      2. Build prompt data per product
      3. Send batches to LLM with structured output schema
      4. Merge LLM results back into original data
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self._model = model
        self._sdk = self._init_sdk()

    # -----------------------------------------------------------------
    # SDK Initialization
    # -----------------------------------------------------------------
    def _init_sdk(self) -> LLM:
        sdk = LLM.default()
        sdk.registry.register(ProviderSpec(
            name="gemini",
            factory=lambda: SyncGeminiClient(
                location=sdk.settings.gemini.location,
            ),
            models={self._model},
        ))
        return sdk

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def execute(self, cmd: EnhanceProductsCommand) -> pd.DataFrame:
        try:
            prompt = Prompt(cmd.prompt_path)
            df = pd.read_excel(cmd.data_file)

            prompt_data = self._build_prompt_data(df)
            all_results = self._process_batches(prompt_data, prompt, cmd.batch_size)

            if not all_results:
                logger.warning("No results from LLM processing.")
                return df

            results_df = pd.DataFrame(all_results)

            # Ensure merge keys have the same type
            df["Código SKU"] = df["Código SKU"].astype(str)
            results_df["id"] = results_df["id"].astype(str)

            final = pd.merge(
                df, results_df,
                left_on="Código SKU", right_on="id",
                how="left",
            )
            final.drop(columns=["id"], inplace=True, errors="ignore")

            logger.info(f"Enhancement complete: {len(all_results)}/{len(df)} products enriched.")
            return final

        except Exception as e:
            logger.error(f"Error enhancing products: {e}", exc_info=True)
            raise

    # -----------------------------------------------------------------
    # Data Preparation
    # -----------------------------------------------------------------
    @staticmethod
    def _build_prompt_data(df: pd.DataFrame) -> list[dict[str, Any]]:
        return [
            {
                "codigo_sku": row["Código SKU"],
                "nombre_producto": row["Nombre del Producto"],
                "negocio": row["Negocio"],
                "direccion": row["Dirección"],
                "seccion": row["Sección"],
            }
            for _, row in df.iterrows()
        ]

    # -----------------------------------------------------------------
    # Batch Processing
    # -----------------------------------------------------------------
    def _process_batches(
        self,
        prompt_data: list[dict],
        prompt: Prompt,
        batch_size: int,
    ) -> list[dict]:

        all_results = []
        total_batches = (len(prompt_data) + batch_size - 1) // batch_size

        batches = [
            prompt_data[i:i + batch_size]
            for i in range(0, len(prompt_data), batch_size)
        ]

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_batch = {
                executor.submit(self._process_single_batch, batch, prompt): idx
                for idx, batch in enumerate(batches, start=1)
            }

            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    result = future.result()
                    if result:
                        all_results.extend(result)
                        logger.info(f"Batch {batch_idx}/{total_batches} processed successfully with {len(result)} results.")
                    else:
                        logger.warning(f"Batch {batch_idx}/{total_batches} returned no results.")
                except Exception as e:
                    logger.error(f"Batch {batch_idx}/{total_batches} failed: {e}", exc_info=True)

        return all_results


    def _process_single_batch(
        self,
        batch: list[dict],
        prompt: Prompt,
    ) -> list[dict] | None:

        prompt_data = prompt.get_prompt(input_data=str(batch))
        system = str(prompt_data.get("system", "")).replace("\n", " ")
        user = str(prompt_data.get("user", "")).replace("\n", " ")
        schema = prompt_data.get("schema")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._sdk.chat(
                    messages=[
                        ChatMessage(
                            role="model",
                            parts=[ChatPart(type="text", text=system)],
                        ),
                        ChatMessage(
                            role="user",
                            parts=[ChatPart(type="text", text=user)],
                        ),
                    ],
                    output_schema=schema,
                    provider="gemini",
                    model=self._model,
                )

                result = json.loads(resp.content)
                return result if isinstance(result, list) else [result]

            except Exception as e:
                logger.warning(
                    f"Batch attempt {attempt}/{MAX_RETRIES} failed: {e}"
                )
                if attempt == MAX_RETRIES:
                    logger.error(f"Batch failed after {MAX_RETRIES} retries.")
                    return None

        return None