"""Base embedder interface and factory."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class EmbeddingProvider(str, Enum):
    """Available embedding providers."""
    
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    BGE = "bge"


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""
    
    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension
        self._total_tokens = 0
        self._total_requests = 0
    
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: The text to embed.
            
        Returns:
            List of floats representing the embedding vector.
        """
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        pass
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get embedding statistics."""
        return {
            "model": self.model_name,
            "dimension": self.dimension,
            "total_tokens": self._total_tokens,
            "total_requests": self._total_requests,
        }


class Embedder:
    """Factory for creating embedders."""
    
    _instance: BaseEmbedder | None = None
    
    @classmethod
    def create(
        cls,
        provider: EmbeddingProvider | str = EmbeddingProvider.OPENAI,
        model_name: str | None = None,
        **kwargs,
    ) -> BaseEmbedder:
        """Create an embedder with the specified provider.
        
        Args:
            provider: The embedding provider to use.
            model_name: Optional model name override.
            **kwargs: Additional arguments for specific embedders.
            
        Returns:
            An embedder instance.
        """
        from app.embeddings.openai_embedder import OpenAIEmbedder
        from app.embeddings.sentence_transformer_embedder import (
            SentenceTransformerEmbedder,
        )
        
        if isinstance(provider, str):
            provider = EmbeddingProvider(provider)
        
        if provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbedder(
                model_name=model_name or "text-embedding-3-small",
                **kwargs,
            )
        elif provider in (
            EmbeddingProvider.SENTENCE_TRANSFORMERS,
            EmbeddingProvider.BGE,
        ):
            default_model = (
                "BAAI/bge-small-en-v1.5"
                if provider == EmbeddingProvider.BGE
                else "all-MiniLM-L6-v2"
            )
            return SentenceTransformerEmbedder(
                model_name=model_name or default_model,
                **kwargs,
            )
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
    
    @classmethod
    def get_default(cls) -> BaseEmbedder:
        """Get or create the default embedder instance."""
        if cls._instance is None:
            from app.config import settings
            
            cls._instance = cls.create(
                provider=settings.embedding_provider,
            )
        
        return cls._instance
