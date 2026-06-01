"""Semantic text chunker using sentence boundaries."""

import re
from typing import Any

from app.chunking.chunker import BaseChunker, Chunk


class SemanticChunker(BaseChunker):
    """Chunks text based on semantic boundaries (sentences, paragraphs)."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.min_chunk_size = min_chunk_size
        
        # Sentence ending patterns
        self.sentence_endings = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Standard sentence end
            r'(?<=[.!?])\s*\n|'          # Sentence end with newline
            r'\n\n+'                      # Paragraph break
        )
    
    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text into semantically meaningful chunks."""
        if metadata is None:
            metadata = {}
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        # Group sentences into chunks
        chunks = self._group_sentences(sentences)
        
        # Create Chunk objects
        result = []
        char_pos = 0
        
        for i, chunk_text in enumerate(chunks):
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
            
            char_pos = max(0, end_char - self.chunk_overlap)
        
        return result
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Split by sentence boundaries
        parts = self.sentence_endings.split(text)
        
        sentences = []
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
        
        return sentences
    
    def _group_sentences(self, sentences: list[str]) -> list[str]:
        """Group sentences into chunks of appropriate size."""
        if not sentences:
            return []
        
        chunks = []
        current_chunk: list[str] = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If single sentence exceeds chunk size, split it
            if sentence_length > self.chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence
                sub_chunks = self._split_long_sentence(sentence)
                chunks.extend(sub_chunks)
                continue
            
            # Check if adding sentence exceeds chunk size
            new_length = current_length + sentence_length + (1 if current_chunk else 0)
            
            if new_length <= self.chunk_size:
                current_chunk.append(sentence)
                current_length = new_length
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, self.chunk_overlap
                )
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Append to previous chunk if too small
                chunks[-1] = chunks[-1] + " " + chunk_text
        
        return chunks
    
    def _split_long_sentence(self, sentence: str) -> list[str]:
        """Split a long sentence into smaller parts."""
        # Try to split by clauses
        clause_separators = ["; ", ", ", " - ", " – "]
        
        for sep in clause_separators:
            if sep in sentence:
                parts = sentence.split(sep)
                if all(len(p) <= self.chunk_size for p in parts):
                    return [p.strip() for p in parts if p.strip()]
        
        # Fall back to word-based splitting
        words = sentence.split()
        chunks = []
        current_chunk: list[str] = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length <= self.chunk_size:
                current_chunk.append(word)
                current_length += word_length
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _get_overlap_sentences(
        self,
        sentences: list[str],
        target_overlap: int,
    ) -> list[str]:
        """Get sentences from the end to create overlap."""
        if not sentences:
            return []
        
        overlap_sentences = []
        current_length = 0
        
        for sentence in reversed(sentences):
            if current_length + len(sentence) <= target_overlap:
                overlap_sentences.insert(0, sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        return overlap_sentences
