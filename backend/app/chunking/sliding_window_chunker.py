"""Sliding window text chunker."""

from typing import Any

from app.chunking.chunker import BaseChunker, Chunk


class SlidingWindowChunker(BaseChunker):
    """Chunks text using a sliding window approach."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        respect_word_boundaries: bool = True,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.respect_word_boundaries = respect_word_boundaries
    
    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text using sliding window."""
        if metadata is None:
            metadata = {}
        
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # If text is smaller than chunk size, return as single chunk
        if len(text) <= self.chunk_size:
            return [
                Chunk(
                    content=text,
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=metadata.copy(),
                )
            ]
        
        chunks = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Adjust boundaries to respect words
            if self.respect_word_boundaries:
                start, end = self._adjust_boundaries(text, start, end)
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = Chunk(
                    content=chunk_text,
                    index=index,
                    start_char=start,
                    end_char=end,
                    metadata=metadata.copy(),
                )
                chunks.append(chunk)
                index += 1
            
            # Move window
            start += step
            
            # Prevent infinite loop
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def _adjust_boundaries(
        self,
        text: str,
        start: int,
        end: int,
    ) -> tuple[int, int]:
        """Adjust start and end to respect word boundaries."""
        # Adjust start to word boundary
        if start > 0 and text[start] != " " and text[start - 1] != " ":
            # Find next space
            next_space = text.find(" ", start)
            if next_space != -1 and next_space < start + 50:
                start = next_space + 1
        
        # Adjust end to word boundary
        if end < len(text) and text[end - 1] != " ":
            # Find previous space
            prev_space = text.rfind(" ", start, end)
            if prev_space != -1 and prev_space > end - 50:
                end = prev_space
        
        return start, end
