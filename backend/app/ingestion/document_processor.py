"""Document processor for orchestrating document ingestion."""

import structlog
from pathlib import Path
from typing import Any

from app.ingestion.base_loader import BaseLoader, DocumentContent
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.markdown_loader import MarkdownLoader
from app.ingestion.docx_loader import DocxLoader
from app.ingestion.html_loader import HTMLLoader
from app.ingestion.text_loader import TextLoader

logger = structlog.get_logger()


class DocumentProcessor:
    """Orchestrates document loading and processing."""
    
    def __init__(self):
        self.loaders: list[BaseLoader] = [
            PDFLoader(),
            MarkdownLoader(),
            DocxLoader(),
            HTMLLoader(),
            TextLoader(),
        ]
    
    def get_loader(self, file_path: str | Path) -> BaseLoader | None:
        """Get the appropriate loader for a file."""
        for loader in self.loaders:
            if loader.can_handle(file_path):
                return loader
        return None
    
    def get_supported_extensions(self) -> list[str]:
        """Get all supported file extensions."""
        extensions = []
        for loader in self.loaders:
            extensions.extend(loader.supported_extensions)
        return extensions
    
    def is_supported(self, file_path: str | Path) -> bool:
        """Check if a file type is supported."""
        return self.get_loader(file_path) is not None
    
    async def process(self, file_path: str | Path) -> DocumentContent:
        """Process a document and extract its content.
        
        Args:
            file_path: Path to the document file.
            
        Returns:
            DocumentContent with extracted text and metadata.
            
        Raises:
            ValueError: If the file type is not supported.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        loader = self.get_loader(file_path)
        
        if loader is None:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported types: {self.get_supported_extensions()}"
            )
        
        logger.info(
            "Processing document",
            file_path=str(file_path),
            loader=loader.__class__.__name__,
        )
        
        try:
            content = await loader.load(file_path)
            
            logger.info(
                "Document processed successfully",
                file_path=str(file_path),
                text_length=len(content.text),
                page_count=content.page_count,
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to process document",
                file_path=str(file_path),
                error=str(e),
            )
            raise
    
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from a document without full processing.
        
        Args:
            file_path: Path to the document file.
            
        Returns:
            Dictionary of metadata.
        """
        file_path = Path(file_path)
        
        loader = self.get_loader(file_path)
        
        if loader is None:
            return {"file_name": file_path.name}
        
        try:
            return await loader.extract_metadata(file_path)
        except Exception as e:
            logger.warning(
                "Failed to extract metadata",
                file_path=str(file_path),
                error=str(e),
            )
            return {"file_name": file_path.name}
    
    async def batch_process(
        self,
        file_paths: list[str | Path],
    ) -> list[tuple[Path, DocumentContent | Exception]]:
        """Process multiple documents.
        
        Args:
            file_paths: List of file paths to process.
            
        Returns:
            List of tuples (file_path, content_or_error).
        """
        results = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            
            try:
                content = await self.process(file_path)
                results.append((file_path, content))
            except Exception as e:
                logger.error(
                    "Batch processing error",
                    file_path=str(file_path),
                    error=str(e),
                )
                results.append((file_path, e))
        
        return results
