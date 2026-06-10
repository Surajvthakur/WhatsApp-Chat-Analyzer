"""
Gemini embedding provider using the google-genai SDK.

Uses the async client (``client.aio.models.embed_content``) so the
FastAPI event loop is never blocked during embedding generation.
"""

import logging
from google import genai
from google.genai import types

from app.ai.base import EmbeddingProvider
from app.config import settings

logger = logging.getLogger(__name__)

# Gemini embed_content accepts at most 100 texts per request.
_MAX_BATCH_SIZE = 100


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Concrete provider that delegates to Google Gemini text-embedding-004."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
        self._dimension = settings.embedding_dimension
        logger.info(
            "GeminiEmbeddingProvider initialised  "
            "(model=%s, dimension=%d)",
            self._model,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed *texts* in batches of 100 (Gemini API limit).

        Returns a flat list of vectors in the same order as *texts*.
        """
        all_vectors: list[list[float]] = []

        for start in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[start : start + _MAX_BATCH_SIZE]
            response = await self._client.aio.models.embed_content(
                model=self._model,
                contents=batch,
                config=types.EmbedContentConfig(
                    output_dimensionality=self._dimension,
                ),
            )
            all_vectors.extend(
                embedding.values for embedding in response.embeddings
            )

        logger.debug("Embedded %d texts → %d vectors", len(texts), len(all_vectors))
        return all_vectors
