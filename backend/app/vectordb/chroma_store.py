"""ChromaDB vector store implementation."""

import asyncio
from pathlib import Path
from typing import Any

import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.vectordb.vector_store import BaseVectorStore, SearchResult

logger = structlog.get_logger()


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB vector store implementation."""
    
    def __init__(
        self,
        collection_name: str = "knowledgepilot",
        dimension: int = 1536,
        persist_directory: str | None = None,
    ):
        super().__init__(collection_name, dimension)
        
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        
        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        
        self.collection = None
    
    async def create_collection(self) -> None:
        """Create or get the collection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_collection_sync)
    
    def _create_collection_sync(self) -> None:
        """Synchronous collection creation."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"dimension": self.dimension},
        )
        
        logger.info(
            "ChromaDB collection ready",
            collection=self.collection_name,
            count=self.collection.count(),
        )
    
    async def delete_collection(self) -> None:
        """Delete the collection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_collection_sync)
    
    def _delete_collection_sync(self) -> None:
        """Synchronous collection deletion."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = None
            logger.info("ChromaDB collection deleted", collection=self.collection_name)
        except Exception as e:
            logger.warning("Failed to delete collection", error=str(e))
    
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        contents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors to the store."""
        if not ids:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._add_sync,
            ids,
            embeddings,
            contents,
            metadatas,
        )
    
    def _add_sync(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        contents: list[str],
        metadatas: list[dict[str, Any]] | None,
    ) -> None:
        """Synchronous add operation."""
        if self.collection is None:
            self._create_collection_sync()
        
        # Clean metadata (ChromaDB doesn't support None values)
        clean_metadatas = None
        if metadatas:
            clean_metadatas = []
            for meta in metadatas:
                clean_meta = {}
                for k, v in meta.items():
                    if v is not None:
                        if isinstance(v, (list, dict)):
                            clean_meta[k] = str(v)
                        else:
                            clean_meta[k] = v
                clean_metadatas.append(clean_meta)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=clean_metadatas,
        )
        
        logger.debug("Added vectors to ChromaDB", count=len(ids))
    
    async def update(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        contents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Update existing vectors."""
        if not ids:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._update_sync,
            ids,
            embeddings,
            contents,
            metadatas,
        )
    
    def _update_sync(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None,
        contents: list[str] | None,
        metadatas: list[dict[str, Any]] | None,
    ) -> None:
        """Synchronous update operation."""
        if self.collection is None:
            return
        
        update_kwargs: dict[str, Any] = {"ids": ids}
        
        if embeddings:
            update_kwargs["embeddings"] = embeddings
        
        if contents:
            update_kwargs["documents"] = contents
        
        if metadatas:
            clean_metadatas = []
            for meta in metadatas:
                clean_meta = {
                    k: (str(v) if isinstance(v, (list, dict)) else v)
                    for k, v in meta.items()
                    if v is not None
                }
                clean_metadatas.append(clean_meta)
            update_kwargs["metadatas"] = clean_metadatas
        
        self.collection.update(**update_kwargs)
    
    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        if not ids:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_sync, ids)
    
    def _delete_sync(self, ids: list[str]) -> None:
        """Synchronous delete operation."""
        if self.collection is None:
            return
        
        self.collection.delete(ids=ids)
        logger.debug("Deleted vectors from ChromaDB", count=len(ids))
    
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_sync,
            query_embedding,
            top_k,
            filter_metadata,
        )
    
    def _search_sync(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_metadata: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Synchronous search operation."""
        if self.collection is None:
            return []
        
        # Build where clause for filtering
        where = None
        if filter_metadata:
            where = {}
            for key, value in filter_metadata.items():
                if value is not None:
                    where[key] = value
            if not where:
                where = None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        search_results = []
        
        if results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            documents = results["documents"][0] if results["documents"] else [""] * len(ids)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
            
            for i, id_ in enumerate(ids):
                # Convert distance to similarity score (ChromaDB uses L2 distance)
                # Lower distance = higher similarity
                score = 1.0 / (1.0 + distances[i])
                
                search_results.append(
                    SearchResult(
                        id=id_,
                        content=documents[i] or "",
                        score=score,
                        metadata=metadatas[i] or {},
                    )
                )
        
        return search_results
    
    async def get_by_ids(self, ids: list[str]) -> list[SearchResult]:
        """Get vectors by their IDs."""
        if not ids:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_by_ids_sync, ids)
    
    def _get_by_ids_sync(self, ids: list[str]) -> list[SearchResult]:
        """Synchronous get by IDs operation."""
        if self.collection is None:
            return []
        
        results = self.collection.get(
            ids=ids,
            include=["documents", "metadatas"],
        )
        
        search_results = []
        
        if results["ids"]:
            for i, id_ in enumerate(results["ids"]):
                search_results.append(
                    SearchResult(
                        id=id_,
                        content=results["documents"][i] if results["documents"] else "",
                        score=1.0,
                        metadata=results["metadatas"][i] if results["metadatas"] else {},
                    )
                )
        
        return search_results
    
    async def count(self) -> int:
        """Get the total number of vectors."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._count_sync)
    
    def _count_sync(self) -> int:
        """Synchronous count operation."""
        if self.collection is None:
            return 0
        return self.collection.count()
    
    async def delete_by_metadata(
        self,
        filter_metadata: dict[str, Any],
    ) -> int:
        """Delete vectors matching metadata filter."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._delete_by_metadata_sync,
            filter_metadata,
        )
    
    def _delete_by_metadata_sync(
        self,
        filter_metadata: dict[str, Any],
    ) -> int:
        """Synchronous delete by metadata operation."""
        if self.collection is None:
            return 0
        
        # Get matching IDs first
        results = self.collection.get(
            where=filter_metadata,
            include=[],
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
        
        return 0
