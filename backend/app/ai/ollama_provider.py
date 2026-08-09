"""
Ollama embedding provider.

Offloads embedding generation to a local or containerized Ollama instance
using the ``/api/embed`` endpoint. Automatically checks for and pulls the
configured model if it is not already available.
"""

import logging
import httpx

from app.ai.base import EmbeddingProvider
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Concrete embedding provider that delegates to an Ollama server."""

    def __init__(self) -> None:
        self._url = settings.ollama_url.rstrip("/")
        self._model = settings.ollama_embedding_model
        self._dimension = settings.embedding_dimension
        self._model_verified = False
        logger.info(
            "OllamaEmbeddingProvider initialized (url=%s, model=%s, dimension=%d)",
            self._url,
            self._model,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    async def _ensure_model_exists(self) -> bool:
        """
        Checks if the configured Ollama embedding model exists, and pulls it if missing.
        """
        if self._model_verified:
            return True

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Check if model exists
                response = await client.post(
                    f"{self._url}/api/show",
                    json={"name": self._model},
                )
                if response.status_code == 200:
                    logger.info("Ollama model '%s' is ready on %s", self._model, self._url)
                    self._model_verified = True
                    return True
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.info("Ollama model '%s' not found. Will attempt to pull...", self._model)
                else:
                    logger.warning("Ollama model check failed with status %s: %s", e.response.status_code, e.response.text)
            except Exception as e:
                logger.warning("Could not connect to Ollama at %s to check model '%s': %s", self._url, self._model, e)
                return False

        # 2. Pull model if missing (extended timeout for download)
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                logger.info("Pulling model '%s' from Ollama registry (this may take a few moments)...", self._model)
                response = await client.post(
                    f"{self._url}/api/pull",
                    json={"name": self._model, "model": self._model, "stream": False},
                )
                if response.status_code == 200:
                    res_data = response.json()
                    if res_data.get("status") == "success":
                        logger.info("Successfully pulled Ollama model '%s'.", self._model)
                        self._model_verified = True
                        return True
                    else:
                        logger.warning("Ollama pull returned status: %s", res_data)
                else:
                    logger.error("Ollama pull failed with status %d: %s", response.status_code, response.text)
            except Exception as e:
                logger.error("Failed to pull model '%s' from Ollama: %s", self._model, e)

        return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed *texts* via Ollama /api/embed in concurrent sub-batches to prevent HTTP timeouts.

        Returns a list of float vectors in the same order as *texts*.
        """
        if not texts:
            return []

        await self._ensure_model_exists()

        import asyncio

        batch_size = 250
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
        total_batches = len(batches)
        logger.info(
            "Embedding %d total chunks via Ollama model '%s' in %d sub-batches...",
            len(texts),
            self._model,
            total_batches,
        )

        semaphore = asyncio.Semaphore(3)

        async def _embed_subbatch(client: httpx.AsyncClient, batch_idx: int, sub_texts: list[str]) -> list[list[float]]:
            async with semaphore:
                try:
                    response = await client.post(
                        f"{self._url}/api/embed",
                        json={"model": self._model, "input": sub_texts},
                    )
                    response.raise_for_status()
                    res_data = response.json()

                    if "embeddings" in res_data:
                        vectors = res_data["embeddings"]
                        logger.info(
                            "Ollama completed batch %d/%d (%d chunks)",
                            batch_idx + 1,
                            total_batches,
                            len(vectors),
                        )
                        return vectors
                    else:
                        raise ValueError("Ollama response missing 'embeddings' field")
                except Exception as e:
                    logger.error("Ollama embedding generation failed for batch %d: %s", batch_idx + 1, e)
                    return [[0.0] * self._dimension for _ in sub_texts]

        async with httpx.AsyncClient(timeout=120.0) as client:
            tasks = [
                _embed_subbatch(client, idx, batch)
                for idx, batch in enumerate(batches)
            ]
            batch_results = await asyncio.gather(*tasks)

        flat_vectors: list[list[float]] = []
        for vectors in batch_results:
            flat_vectors.extend(vectors)

        logger.info("Ollama completed all %d vectors successfully.", len(flat_vectors))
        return flat_vectors
