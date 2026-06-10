"""
Abstract base class for embedding providers.

All embedding providers must implement this interface, making it trivial
to swap Gemini for OpenAI, Cohere, or any other provider via config.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Contract that every embedding provider must fulfill."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embedding vectors for a batch of texts.

        Args:
            texts: Non-empty list of strings to embed.

        Returns:
            List of float vectors, one per input text.
            Each vector has length equal to ``self.dimension``.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the vectors produced by this provider."""
