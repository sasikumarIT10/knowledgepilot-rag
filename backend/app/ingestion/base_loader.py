"""Base document loader interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocumentContent:
    """Represents extracted document content."""
    
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[dict[str, Any]] = field(default_factory=list)
    
    @property
    def page_count(self) -> int:
        """Get the number of pages."""
        return len(self.pages) if self.pages else 1
    
    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.text.split())


class BaseLoader(ABC):
    """Abstract base class for document loaders."""
    
    supported_extensions: list[str] = []
    
    @classmethod
    def can_handle(cls, file_path: str | Path) -> bool:
        """Check if this loader can handle the given file."""
        ext = Path(file_path).suffix.lower().lstrip(".")
        return ext in cls.supported_extensions
    
    @abstractmethod
    async def load(self, file_path: str | Path) -> DocumentContent:
        """Load and extract content from a document.
        
        Args:
            file_path: Path to the document file.
            
        Returns:
            DocumentContent with extracted text and metadata.
        """
        pass
    
    @abstractmethod
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from a document.
        
        Args:
            file_path: Path to the document file.
            
        Returns:
            Dictionary of metadata.
        """
        pass
