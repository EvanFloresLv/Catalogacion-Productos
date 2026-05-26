# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from concurrent.futures import ThreadPoolExecutor


class EmbeddingPipeline:

    def __init__(self, embedding_service, batch_size: int = 50, max_workers: int = 4):
        self._embedding_service = embedding_service
        self._batch_size = batch_size
        self._max_workers = max_workers


    def generate(self, product_data: dict) -> dict[str, list[float]]:

        texts = {
            sku: data["embedding_text"]
            for sku, data in product_data.items()
        }

        if not texts:
            return {}

        skus = list(texts.keys())
        values = [texts[sku] for sku in skus]

        vectors: list[list[float]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:

            futures = [
                executor.submit(
                    self._embedding_service.generate_batch,
                    values[i:i + self._batch_size],
                )
                for i in range(0, len(values), self._batch_size)
            ]

            for future in futures:
                vectors.extend(future.result())

        return dict(zip(skus, vectors))