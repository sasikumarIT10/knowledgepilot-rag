"""OpenAI embeddings provider."""

import asyncio
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.embeddings.embedder import BaseEmbedder

logger = structlog.get_logger()


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings provider."""
    
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: str | None = None,
        batch_size: int = 100,
    ):
        dimension = self.MODEL_DIMENSIONS.get(model_name, 1536)
        super().__init__(model_name, dimension)
        
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
        )
        self.batch_size = batch_size
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            
            self._total_requests += 1
            self._total_tokens += response.usage.total_tokens
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error("OpenAI embedding error", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        # Filter empty texts and track indices
        valid_texts = []
        valid_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            return [[0.0] * self.dimension for _ in texts]
        
        # Process in batches
        all_embeddings: dict[int, list[float]] = {}
        
        for batch_start in range(0, len(valid_texts), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(valid_texts))
            batch_texts = valid_texts[batch_start:batch_end]
            batch_indices = valid_indices[batch_start:batch_end]
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=batch_texts,
                )
                
                self._total_requests += 1
                self._total_tokens += response.usage.total_tokens
                
                for j, embedding_data in enumerate(response.data):
                    original_idx = batch_indices[j]
                    all_embeddings[original_idx] = embedding_data.embedding
                    
            except Exception as e:
                logger.error(
                    "OpenAI batch embedding error",
                    batch_start=batch_start,
                    error=str(e),
                )
                raise
        
        # Reconstruct results in original order
        results = []
        for i in range(len(texts)):
            if i in all_embeddings:
                results.append(all_embeddings[i])
            else:
                results.append([0.0] * self.dimension)
        
        return results
    
    async def embed_with_cache(
        self,
        texts: list[str],
        cache: dict[str, list[float]] | None = None,
    ) -> tuple[list[list[float]], dict[str, list[float]]]:
        """Embed texts with caching support.
        
        Args:
            texts: List of texts to embed.
            cache: Optional cache dictionary.
            
        Returns:
            Tuple of (embeddings, updated_cache).
        """
        if cache is None:
            cache = {}
        
        # Find texts that need embedding
        texts_to_embed = []
        indices_to_embed = []
        
        for i, text in enumerate(texts):
            if text not in cache:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # Embed new texts
        if texts_to_embed:
            new_embeddings = await self.embed_batch(texts_to_embed)
            
            for text, embedding in zip(texts_to_embed, new_embeddings):
                cache[text] = embedding
        
        # Build results
        results = [cache.get(text, [0.0] * self.dimension) for text in texts]
        
        return results, cache
