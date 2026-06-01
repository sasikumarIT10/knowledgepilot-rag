"""HTML document loader."""

import asyncio
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.ingestion.base_loader import BaseLoader, DocumentContent


class HTMLLoader(BaseLoader):
    """Loader for HTML documents."""
    
    supported_extensions = ["html", "htm"]
    
    async def load(self, file_path: str | Path) -> DocumentContent:
        """Load and extract content from an HTML file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._load_sync, file_path)
    
    def _load_sync(self, file_path: Path) -> DocumentContent:
        """Synchronous HTML loading."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        soup = BeautifulSoup(content, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        # Extract text
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()
        
        # Extract metadata
        metadata = self._extract_metadata_sync(soup)
        metadata["file_name"] = file_path.name
        
        # Create sections from headers
        pages = self._extract_sections(soup)
        
        return DocumentContent(
            text=text,
            metadata=metadata,
            pages=pages,
        )
    
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from an HTML file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._extract_metadata_from_file, file_path
        )
    
    def _extract_metadata_from_file(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from HTML file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        soup = BeautifulSoup(content, "html.parser")
        return self._extract_metadata_sync(soup)
    
    def _extract_metadata_sync(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract metadata from BeautifulSoup object."""
        metadata: dict[str, Any] = {}
        
        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()
        
        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            content = meta.get("content", "")
            
            if name == "author":
                metadata["author"] = content
            elif name == "description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = content
            elif name == "date" or name == "created":
                metadata["creation_date"] = content
        
        # Open Graph tags
        for meta in soup.find_all("meta", property=True):
            prop = meta.get("property", "").lower()
            content = meta.get("content", "")
            
            if prop == "og:title" and "title" not in metadata:
                metadata["title"] = content
            elif prop == "og:description" and "description" not in metadata:
                metadata["description"] = content
        
        return metadata
    
    def _extract_sections(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract sections based on headers."""
        pages = []
        page_num = 1
        
        # Find all headers
        headers = soup.find_all(["h1", "h2", "h3"])
        
        if not headers:
            # No headers, return entire content as one page
            text = soup.get_text(separator="\n").strip()
            return [{"page_number": 1, "text": text, "title": ""}]
        
        for i, header in enumerate(headers):
            title = header.get_text().strip()
            level = int(header.name[1])
            
            # Get content until next header
            content_parts = [title]
            for sibling in header.find_next_siblings():
                if sibling.name in ["h1", "h2", "h3"]:
                    break
                text = sibling.get_text().strip()
                if text:
                    content_parts.append(text)
            
            pages.append({
                "page_number": page_num,
                "text": "\n".join(content_parts),
                "title": title,
                "level": level,
            })
            page_num += 1
        
        return pages
