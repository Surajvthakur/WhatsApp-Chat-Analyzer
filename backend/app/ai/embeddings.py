"""
Embedding service factory.

Resolves the configured provider once and exposes a single async function
``generate_embeddings`` that the rest of the codebase calls.
"""

import logging
from functools import lru_cache

from app.ai.base import EmbeddingProvider
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "gemini": "app.ai.gemini_provider.GeminiEmbeddingProvider",
}


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """
    Return the singleton embedding provider based on ``EMBEDDING_PROVIDER``.

    Raises ``ValueError`` if the configured provider is unknown.
    """
    provider_key = settings.embedding_provider.lower()

    if provider_key not in _PROVIDERS:
        raise ValueError(
            f"Unknown embedding provider '{provider_key}'. "
            f"Supported: {', '.join(_PROVIDERS)}"
        )

    module_path, class_name = _PROVIDERS[provider_key].rsplit(".", 1)

    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    instance = cls()
    logger.info("Embedding provider ready: %s", provider_key)
    return instance


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for *texts* using the active provider.

    This is the **only** function the rest of the codebase should call.
    """
    if not texts:
        return []

    provider = get_embedding_provider()
    return await provider.embed(texts)
