"""Base vector store interface and factory."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class VectorDBType(str, Enum):
    """Available vector database types."""
    
    CHROMADB = "chromadb"
    PINECONE = "pinecone"
    FAISS = "faiss"


@dataclass
class SearchResult:
    """Represents a vector search result."""
    
    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def document_id(self) -> str | None:
        """Get the source document ID."""
        return self.metadata.get("document_id")
    
    @property
    def chunk_index(self) -> int | None:
        """Get the chunk index."""
        return self.metadata.get("chunk_index")
    
    @property
    def page_number(self) -> int | None:
        """Get the page number."""
        return self.metadata.get("page_number")


class BaseVectorStore(ABC):
    """Abstract base class for vector stores."""
    
    def __init__(self, collection_name: str, dimension: int):
        self.collection_name = collection_name
        self.dimension = dimension
    
    @abstractmethod
    async def create_collection(self) -> None:
        """Create or get the collection."""
        pass
    
    @abstractmethod
    async def delete_collection(self) -> None:
        """Delete the collection."""
        pass
    
    @abstractmethod
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        contents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors to the store.
        
        Args:
            ids: Unique identifiers for each vector.
            embeddings: List of embedding vectors.
            contents: Original text content for each vector.
            metadatas: Optional metadata for each vector.
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        contents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Update existing vectors."""
        pass
    
    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors.
        
        Args:
            query_embedding: The query vector.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filters.
            
        Returns:
            List of SearchResult objects.
        """
        pass
    
    @abstractmethod
    async def get_by_ids(self, ids: list[str]) -> list[SearchResult]:
        """Get vectors by their IDs."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get the total number of vectors."""
        pass


class VectorStore:
    """Factory for creating vector stores."""
    
    _instance: BaseVectorStore | None = None
    
    @classmethod
    def create(
        cls,
        db_type: VectorDBType | str = VectorDBType.CHROMADB,
        collection_name: str = "knowledgepilot",
        dimension: int = 1536,
        **kwargs,
    ) -> BaseVectorStore:
        """Create a vector store with the specified type.
        
        Args:
            db_type: The vector database type.
            collection_name: Name of the collection.
            dimension: Embedding dimension.
            **kwargs: Additional arguments for specific stores.
            
        Returns:
            A vector store instance.
        """
        from app.vectordb.chroma_store import ChromaVectorStore
        
        if isinstance(db_type, str):
            db_type = VectorDBType(db_type)
        
        if db_type == VectorDBType.CHROMADB:
            return ChromaVectorStore(
                collection_name=collection_name,
                dimension=dimension,
                **kwargs,
            )
        elif db_type == VectorDBType.FAISS:
            # FAISS implementation would go here
            raise NotImplementedError("FAISS support coming soon")
        elif db_type == VectorDBType.PINECONE:
            # Pinecone implementation would go here
            raise NotImplementedError("Pinecone support coming soon")
        else:
            raise ValueError(f"Unknown vector database type: {db_type}")
    
    @classmethod
    async def get_default(cls) -> BaseVectorStore:
        """Get or create the default vector store instance."""
        if cls._instance is None:
            from app.config import settings
            
            cls._instance = cls.create(
                db_type=settings.vector_db_type,
                collection_name=settings.chroma_collection_name,
                dimension=settings.embedding_dimension,
                persist_directory=settings.chroma_persist_directory,
            )
            await cls._instance.create_collection()
        
        return cls._instance
