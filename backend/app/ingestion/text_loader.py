"""Plain text document loader."""

import asyncio
from pathlib import Path
from typing import Any

from app.ingestion.base_loader import BaseLoader, DocumentContent


class TextLoader(BaseLoader):
    """Loader for plain text documents."""
    
    supported_extensions = ["txt", "text"]
    
    async def load(self, file_path: str | Path) -> DocumentContent:
        """Load and extract content from a text file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._load_sync, file_path)
    
    def _load_sync(self, file_path: Path) -> DocumentContent:
        """Synchronous text loading."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        metadata = {
            "file_name": file_path.name,
            "char_count": len(text),
            "line_count": text.count("\n") + 1,
        }
        
        # Split into pages by double newlines or every N lines
        pages = self._create_pages(text)
        
        return DocumentContent(
            text=text,
            metadata=metadata,
            pages=pages,
        )
    
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from a text file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._extract_metadata_sync, file_path
        )
    
    def _extract_metadata_sync(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata synchronously."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Try to extract title from first line
        lines = text.split("\n")
        title = lines[0].strip() if lines else ""
        
        return {
            "file_name": file_path.name,
            "title": title[:100] if title else None,
            "char_count": len(text),
            "line_count": len(lines),
        }
    
    def _create_pages(
        self,
        text: str,
        lines_per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Create pages from text content."""
        # First try to split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")
        
        if len(paragraphs) > 1:
            pages = []
            for i, para in enumerate(paragraphs, start=1):
                para = para.strip()
                if para:
                    pages.append({
                        "page_number": i,
                        "text": para,
                    })
            return pages if pages else [{"page_number": 1, "text": text}]
        
        # Otherwise split by lines
        lines = text.split("\n")
        pages = []
        page_num = 1
        
        for i in range(0, len(lines), lines_per_page):
            page_lines = lines[i:i + lines_per_page]
            page_text = "\n".join(page_lines).strip()
            
            if page_text:
                pages.append({
                    "page_number": page_num,
                    "text": page_text,
                })
                page_num += 1
        
        return pages if pages else [{"page_number": 1, "text": text}]
