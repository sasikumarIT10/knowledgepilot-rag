"""Retriever for RAG pipeline."""

import structlog
from typing import Any

from app.config import settings
from app.embeddings.embedder import Embedder
from app.vectordb.vector_store import VectorStore, SearchResult

logger = structlog.get_logger()


class Retriever:
    """Handles document retrieval for RAG."""
    
    def __init__(
        self,
        embedder=None,
        vector_store=None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ):
        self._embedder = embedder
        self._vector_store = vector_store
        self.top_k = top_k or settings.rag_top_k
        self.similarity_threshold = similarity_threshold or settings.rag_similarity_threshold
    
    async def _get_embedder(self):
        """Get or create embedder."""
        if self._embedder is None:
            self._embedder = Embedder.get_default()
        return self._embedder
    
    async def _get_vector_store(self):
        """Get or create vector store."""
        if self._vector_store is None:
            self._vector_store = await VectorStore.get_default()
        return self._vector_store
    
    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_user_id: str | None = None,
        filter_document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents for a query.
        
        Args:
            query: The search query.
            top_k: Number of results to return.
            filter_user_id: Filter by user ID.
            filter_document_ids: Filter by specific document IDs.
            
        Returns:
            List of retrieved chunks with content and metadata.
        """
        top_k = top_k or self.top_k
        
        logger.info("Retrieving documents", query=query[:100], top_k=top_k)
        
        # Generate query embedding
        embedder = await self._get_embedder()
        query_embedding = await embedder.embed(query)
        
        # Build metadata filter
        filter_metadata = {}
        if filter_user_id:
            filter_metadata["user_id"] = filter_user_id
        
        # Search vector store
        vector_store = await self._get_vector_store()
        results = await vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more for filtering
            filter_metadata=filter_metadata if filter_metadata else None,
        )
        
        # Filter by document IDs if specified
        if filter_document_ids:
            results = [
                r for r in results
                if r.metadata.get("document_id") in filter_document_ids
            ]
        
        # Filter by similarity threshold
        results = [
            r for r in results
            if r.score >= self.similarity_threshold
        ]
        
        # Limit to top_k
        results = results[:top_k]
        
        logger.info(
            "Retrieved documents",
            count=len(results),
            scores=[r.score for r in results],
        )
        
        # Convert to dictionaries
        return [
            {
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ]
    
    async def hybrid_retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_user_id: str | None = None,
        keyword_weight: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Hybrid retrieval combining semantic and keyword search.
        
        Args:
            query: The search query.
            top_k: Number of results to return.
            filter_user_id: Filter by user ID.
            keyword_weight: Weight for keyword matching (0-1).
            
        Returns:
            List of retrieved chunks with combined scores.
        """
        top_k = top_k or self.top_k
        
        # Get semantic results
        semantic_results = await self.retrieve(
            query=query,
            top_k=top_k * 2,
            filter_user_id=filter_user_id,
        )
        
        # Simple keyword matching boost
        query_terms = set(query.lower().split())
        
        for result in semantic_results:
            content_lower = result["content"].lower()
            
            # Count matching terms
            matches = sum(1 for term in query_terms if term in content_lower)
            keyword_score = matches / len(query_terms) if query_terms else 0
            
            # Combine scores
            semantic_weight = 1 - keyword_weight
            result["score"] = (
                result["score"] * semantic_weight +
                keyword_score * keyword_weight
            )
        
        # Re-sort by combined score
        semantic_results.sort(key=lambda x: x["score"], reverse=True)
        
        return semantic_results[:top_k]
    
    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rerank results using cross-encoder (if available).
        
        Args:
            query: The original query.
            results: Initial retrieval results.
            top_k: Number of results to return after reranking.
            
        Returns:
            Reranked results.
        """
        if not settings.rag_rerank_enabled:
            return results[:top_k] if top_k else results
        
        top_k = top_k or self.top_k
        
        try:
            from sentence_transformers import CrossEncoder
            
            # Load cross-encoder model
            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            
            # Prepare pairs
            pairs = [(query, r["content"]) for r in results]
            
            # Get rerank scores
            scores = model.predict(pairs)
            
            # Update scores
            for i, result in enumerate(results):
                result["rerank_score"] = float(scores[i])
                result["original_score"] = result["score"]
                result["score"] = float(scores[i])
            
            # Sort by rerank score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info("Reranked results", count=len(results))
            
        except ImportError:
            logger.warning("Cross-encoder not available, skipping reranking")
        except Exception as e:
            logger.error("Reranking failed", error=str(e))
        
        return results[:top_k]
    
    def calculate_confidence(
        self,
        results: list[dict[str, Any]],
    ) -> float:
        """Calculate overall confidence score for retrieval.
        
        Args:
            results: Retrieved results.
            
        Returns:
            Confidence score between 0 and 1.
        """
        if not results:
            return 0.0
        
        # Factors for confidence:
        # 1. Top result score
        # 2. Average score
        # 3. Number of relevant results
        
        top_score = results[0]["score"]
        avg_score = sum(r["score"] for r in results) / len(results)
        coverage = min(len(results) / self.top_k, 1.0)
        
        # Weighted combination
        confidence = (
            top_score * 0.5 +
            avg_score * 0.3 +
            coverage * 0.2
        )
        
        return min(max(confidence, 0.0), 1.0)
