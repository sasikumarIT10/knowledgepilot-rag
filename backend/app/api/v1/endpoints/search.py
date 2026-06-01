"""Search endpoints."""

from typing import Any

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.dependencies import DbSession, CurrentUser
from app.rag.retriever import Retriever
from app.vectordb.vector_store import VectorStore

logger = structlog.get_logger()
router = APIRouter()


class SearchResult(BaseModel):
    """Search result schema."""
    
    id: str
    content: str
    score: float
    document_id: str | None
    document_name: str | None
    page_number: int | None
    chunk_index: int | None


class SearchResponse(BaseModel):
    """Search response schema."""
    
    query: str
    results: list[SearchResult]
    total: int


class VectorSearchVisualization(BaseModel):
    """Vector search visualization data."""
    
    query: str
    query_embedding_preview: list[float]  # First 10 dimensions
    results: list[dict[str, Any]]


@router.get("", response_model=SearchResponse)
async def search_documents(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(default=10, ge=1, le=50, description="Number of results"),
    document_ids: str | None = Query(default=None, description="Comma-separated document IDs"),
):
    """Search across all documents using semantic search."""
    retriever = Retriever()
    
    # Parse document IDs filter
    doc_id_list = None
    if document_ids:
        doc_id_list = [d.strip() for d in document_ids.split(",") if d.strip()]
    
    # Perform search
    results = await retriever.retrieve(
        query=q,
        top_k=top_k,
        filter_user_id=current_user.id,
        filter_document_ids=doc_id_list,
    )
    
    # Format results
    search_results = []
    for result in results:
        metadata = result.get("metadata", {})
        search_results.append(
            SearchResult(
                id=result["id"],
                content=result["content"],
                score=result["score"],
                document_id=metadata.get("document_id"),
                document_name=metadata.get("document_name"),
                page_number=metadata.get("page_number"),
                chunk_index=metadata.get("chunk_index"),
            )
        )
    
    return SearchResponse(
        query=q,
        results=search_results,
        total=len(search_results),
    )


@router.get("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(default=10, ge=1, le=50, description="Number of results"),
    keyword_weight: float = Query(default=0.3, ge=0, le=1, description="Keyword weight"),
):
    """Hybrid search combining semantic and keyword matching."""
    retriever = Retriever()
    
    results = await retriever.hybrid_retrieve(
        query=q,
        top_k=top_k,
        filter_user_id=current_user.id,
        keyword_weight=keyword_weight,
    )
    
    search_results = []
    for result in results:
        metadata = result.get("metadata", {})
        search_results.append(
            SearchResult(
                id=result["id"],
                content=result["content"],
                score=result["score"],
                document_id=metadata.get("document_id"),
                document_name=metadata.get("document_name"),
                page_number=metadata.get("page_number"),
                chunk_index=metadata.get("chunk_index"),
            )
        )
    
    return SearchResponse(
        query=q,
        results=search_results,
        total=len(search_results),
    )


@router.get("/visualize", response_model=VectorSearchVisualization)
async def visualize_search(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
):
    """Get vector search visualization data."""
    from app.embeddings.embedder import Embedder
    
    # Get query embedding
    embedder = Embedder.get_default()
    query_embedding = await embedder.embed(q)
    
    # Perform search
    retriever = Retriever()
    results = await retriever.retrieve(
        query=q,
        top_k=top_k,
        filter_user_id=current_user.id,
    )
    
    # Format for visualization
    viz_results = []
    for result in results:
        metadata = result.get("metadata", {})
        viz_results.append({
            "id": result["id"],
            "content_preview": result["content"][:200],
            "score": result["score"],
            "document_name": metadata.get("document_name", "Unknown"),
            "page_number": metadata.get("page_number"),
        })
    
    return VectorSearchVisualization(
        query=q,
        query_embedding_preview=query_embedding[:10],  # First 10 dimensions
        results=viz_results,
    )


@router.get("/stats")
async def get_search_stats(
    db: DbSession,
    current_user: CurrentUser,
):
    """Get vector store statistics."""
    vector_store = await VectorStore.get_default()
    
    total_vectors = await vector_store.count()
    
    return {
        "total_vectors": total_vectors,
        "collection_name": vector_store.collection_name,
        "dimension": vector_store.dimension,
    }
