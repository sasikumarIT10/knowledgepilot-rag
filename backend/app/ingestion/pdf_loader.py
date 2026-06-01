"""PDF document loader."""

import asyncio
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.ingestion.base_loader import BaseLoader, DocumentContent


class PDFLoader(BaseLoader):
    """Loader for PDF documents."""
    
    supported_extensions = ["pdf"]
    
    async def load(self, file_path: str | Path) -> DocumentContent:
        """Load and extract content from a PDF file."""
        file_path = Path(file_path)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._load_sync, file_path)
    
    def _load_sync(self, file_path: Path) -> DocumentContent:
        """Synchronous PDF loading."""
        reader = PdfReader(file_path)
        
        pages = []
        full_text_parts = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            
            pages.append({
                "page_number": page_num,
                "text": text,
                "char_count": len(text),
            })
            
            full_text_parts.append(text)
        
        full_text = "\n\n".join(full_text_parts)
        
        # Extract metadata
        metadata = self._extract_metadata_sync(reader)
        metadata["page_count"] = len(reader.pages)
        metadata["file_name"] = file_path.name
        
        return DocumentContent(
            text=full_text,
            metadata=metadata,
            pages=pages,
        )
    
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from a PDF file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._extract_metadata_from_file, file_path
        )
    
    def _extract_metadata_from_file(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from PDF file."""
        reader = PdfReader(file_path)
        return self._extract_metadata_sync(reader)
    
    def _extract_metadata_sync(self, reader: PdfReader) -> dict[str, Any]:
        """Extract metadata from PDF reader."""
        metadata: dict[str, Any] = {}
        
        if reader.metadata:
            pdf_meta = reader.metadata
            
            if pdf_meta.title:
                metadata["title"] = pdf_meta.title
            
            if pdf_meta.author:
                metadata["author"] = pdf_meta.author
            
            if pdf_meta.subject:
                metadata["subject"] = pdf_meta.subject
            
            if pdf_meta.creator:
                metadata["creator"] = pdf_meta.creator
            
            if pdf_meta.producer:
                metadata["producer"] = pdf_meta.producer
            
            if pdf_meta.creation_date:
                metadata["creation_date"] = str(pdf_meta.creation_date)
            
            if pdf_meta.modification_date:
                metadata["modification_date"] = str(pdf_meta.modification_date)
        
        return metadata
