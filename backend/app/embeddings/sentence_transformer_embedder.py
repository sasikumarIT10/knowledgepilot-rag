"""Sentence Transformers embeddings provider."""

import asyncio
from typing import Any

import structlog

from app.embeddings.embedder import BaseEmbedder

logger = structlog.get_logger()


class SentenceTransformerEmbedder(BaseEmbedder):
    """Sentence Transformers embeddings provider (local models)."""
    
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
    }
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
        batch_size: int = 32,
    ):
        dimension = self.MODEL_DIMENSIONS.get(model_name, 384)
        super().__init__(model_name, dimension)
        
        self.batch_size = batch_size
        self._model = None
        self._device = device
    
    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                logger.info(
                    "Loading SentenceTransformer model",
                    model=self.model_name,
                )
                
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self._device,
                )
                
                # Update dimension from model
                self.dimension = self._model.get_sentence_embedding_dimension()
                
                logger.info(
                    "Model loaded",
                    model=self.model_name,
                    dimension=self.dimension,
                )
                
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. "
                    "Install with: pip install sentence-transformers"
                )
        
        return self._model
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, text)
    
    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous embedding."""
        model = self._load_model()
        
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        
        self._total_requests += 1
        
        return embedding.tolist()
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_batch_sync, texts)
    
    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding."""
        model = self._load_model()
        
        # Handle empty texts
        valid_texts = []
        valid_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            return [[0.0] * self.dimension for _ in texts]
        
        # Encode all valid texts
        embeddings = model.encode(
            valid_texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        
        self._total_requests += 1
        
        # Reconstruct results
        results = [[0.0] * self.dimension for _ in texts]
        
        for i, idx in enumerate(valid_indices):
            results[idx] = embeddings[i].tolist()
        
        return results
