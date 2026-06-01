"""Base chunker interface and factory."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class Chunk:
    """Represents a text chunk."""
    
    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


class BaseChunker(ABC):
    """Abstract base class for text chunkers."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text into chunks.
        
        Args:
            text: The text to chunk.
            metadata: Optional metadata to include in each chunk.
            
        Returns:
            List of Chunk objects.
        """
        pass
    
    def chunk_with_pages(
        self,
        pages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Chunk text while preserving page information.
        
        Args:
            pages: List of page dictionaries with 'text' and 'page_number'.
            metadata: Optional metadata to include in each chunk.
            
        Returns:
            List of Chunk objects with page information.
        """
        all_chunks = []
        global_index = 0
        char_offset = 0
        
        for page in pages:
            page_text = page.get("text", "")
            page_number = page.get("page_number", 1)
            
            if not page_text.strip():
                continue
            
            page_chunks = self.chunk(page_text, metadata)
            
            for chunk in page_chunks:
                chunk.index = global_index
                chunk.start_char += char_offset
                chunk.end_char += char_offset
                chunk.metadata["page_number"] = page_number
                
                if "title" in page:
                    chunk.metadata["section_title"] = page["title"]
                
                all_chunks.append(chunk)
                global_index += 1
            
            char_offset += len(page_text)
        
        return all_chunks


class Chunker:
    """Factory for creating chunkers."""
    
    @staticmethod
    def create(
        strategy: ChunkingStrategy | str = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs,
    ) -> BaseChunker:
        """Create a chunker with the specified strategy.
        
        Args:
            strategy: The chunking strategy to use.
            chunk_size: Target size for each chunk.
            chunk_overlap: Overlap between consecutive chunks.
            **kwargs: Additional arguments for specific chunkers.
            
        Returns:
            A chunker instance.
        """
        from app.chunking.recursive_chunker import RecursiveCharacterChunker
        from app.chunking.semantic_chunker import SemanticChunker
        from app.chunking.sliding_window_chunker import SlidingWindowChunker
        
        if isinstance(strategy, str):
            strategy = ChunkingStrategy(strategy)
        
        if strategy == ChunkingStrategy.RECURSIVE:
            return RecursiveCharacterChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                **kwargs,
            )
        elif strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                **kwargs,
            )
        elif strategy == ChunkingStrategy.SLIDING_WINDOW:
            return SlidingWindowChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                **kwargs,
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
