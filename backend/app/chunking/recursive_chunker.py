"""Recursive character text splitter."""

from typing import Any

from app.chunking.chunker import BaseChunker, Chunk


class RecursiveCharacterChunker(BaseChunker):
    """Recursively splits text using a hierarchy of separators."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        super().__init__(chunk_size, chunk_overlap)
        
        self.separators = separators or [
            "\n\n",  # Paragraphs
            "\n",    # Lines
            ". ",    # Sentences
            ", ",    # Clauses
            " ",     # Words
            "",      # Characters
        ]
    
    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text recursively using separators."""
        if metadata is None:
            metadata = {}
        
        chunks = self._split_text(text, self.separators)
        
        result = []
        char_pos = 0
        
        for i, chunk_text in enumerate(chunks):
            # Find actual position in original text
            start_char = text.find(chunk_text, char_pos)
            if start_char == -1:
                start_char = char_pos
            
            end_char = start_char + len(chunk_text)
            
            chunk = Chunk(
                content=chunk_text,
                index=i,
                start_char=start_char,
                end_char=end_char,
                metadata=metadata.copy(),
            )
            result.append(chunk)
            
            # Update position for next search
            char_pos = start_char + len(chunk_text) - self.chunk_overlap
            if char_pos < 0:
                char_pos = 0
        
        return result
    
    def _split_text(
        self,
        text: str,
        separators: list[str],
    ) -> list[str]:
        """Recursively split text using separators."""
        if not text:
            return []
        
        # If text is small enough, return it
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []
        
        # Find the best separator
        separator = ""
        for sep in separators:
            if sep in text:
                separator = sep
                break
        
        # If no separator found, split by characters
        if separator == "":
            return self._split_by_characters(text)
        
        # Split by separator
        splits = text.split(separator)
        
        # Merge small splits
        chunks = []
        current_chunk = ""
        
        for split in splits:
            split = split.strip()
            if not split:
                continue
            
            # Check if adding this split exceeds chunk size
            test_chunk = current_chunk + separator + split if current_chunk else split
            
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If split itself is too large, recursively split it
                if len(split) > self.chunk_size:
                    # Use remaining separators
                    remaining_seps = separators[separators.index(separator) + 1:]
                    if remaining_seps:
                        sub_chunks = self._split_text(split, remaining_seps)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        chunks.extend(self._split_by_characters(split))
                        current_chunk = ""
                else:
                    current_chunk = split
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Apply overlap
        return self._apply_overlap(chunks)
    
    def _split_by_characters(self, text: str) -> list[str]:
        """Split text by character count with overlap."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
            if start >= len(text):
                break
        
        return chunks
    
    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Apply overlap between chunks."""
        if len(chunks) <= 1 or self.chunk_overlap == 0:
            return chunks
        
        result = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                result.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = ""
                
                if len(prev_chunk) > self.chunk_overlap:
                    overlap_text = prev_chunk[-self.chunk_overlap:]
                    # Try to start at a word boundary
                    space_idx = overlap_text.find(" ")
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx + 1:]
                
                # Combine overlap with current chunk
                combined = overlap_text + " " + chunk if overlap_text else chunk
                
                # Trim if too long
                if len(combined) > self.chunk_size:
                    combined = combined[:self.chunk_size]
                    # Try to end at a word boundary
                    last_space = combined.rfind(" ")
                    if last_space > self.chunk_size * 0.8:
                        combined = combined[:last_space]
                
                result.append(combined.strip())
        
        return result
