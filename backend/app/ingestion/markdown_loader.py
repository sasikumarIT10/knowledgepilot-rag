"""Markdown document loader."""

import asyncio
import re
from pathlib import Path
from typing import Any

import markdown
from bs4 import BeautifulSoup

from app.ingestion.base_loader import BaseLoader, DocumentContent


class MarkdownLoader(BaseLoader):
    """Loader for Markdown documents."""
    
    supported_extensions = ["md", "markdown"]
    
    async def load(self, file_path: str | Path) -> DocumentContent:
        """Load and extract content from a Markdown file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._load_sync, file_path)
    
    def _load_sync(self, file_path: Path) -> DocumentContent:
        """Synchronous Markdown loading."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Convert Markdown to HTML
        html = markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "codehilite", "toc"],
        )
        
        # Extract plain text from HTML
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        
        # Extract metadata from frontmatter if present
        metadata = self._extract_frontmatter(content)
        metadata["file_name"] = file_path.name
        
        # Extract headers as sections
        sections = self._extract_sections(content)
        
        # Create pages from sections (treat each H1/H2 as a page)
        pages = []
        for i, section in enumerate(sections, start=1):
            pages.append({
                "page_number": i,
                "text": section["content"],
                "title": section.get("title", ""),
                "level": section.get("level", 1),
            })
        
        if not pages:
            pages = [{"page_number": 1, "text": text}]
        
        return DocumentContent(
            text=text,
            metadata=metadata,
            pages=pages,
        )
    
    async def extract_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Extract metadata from a Markdown file."""
        file_path = Path(file_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._extract_metadata_sync, file_path
        )
    
    def _extract_metadata_sync(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata synchronously."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        metadata = self._extract_frontmatter(content)
        metadata["file_name"] = file_path.name
        
        # Extract title from first H1 if not in frontmatter
        if "title" not in metadata:
            match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if match:
                metadata["title"] = match.group(1).strip()
        
        return metadata
    
    def _extract_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from Markdown."""
        metadata: dict[str, Any] = {}
        
        # Check for YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                
                # Simple YAML parsing (key: value)
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip().lower()] = value.strip()
        
        return metadata
    
    def _extract_sections(self, content: str) -> list[dict[str, Any]]:
        """Extract sections based on headers."""
        sections = []
        
        # Split by headers
        pattern = r"^(#{1,6})\s+(.+)$"
        lines = content.split("\n")
        
        current_section: dict[str, Any] | None = None
        current_content: list[str] = []
        
        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Save previous section
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)
                
                # Start new section
                level = len(match.group(1))
                title = match.group(2).strip()
                current_section = {
                    "title": title,
                    "level": level,
                }
                current_content = [line]
            else:
                current_content.append(line)
        
        # Save last section
        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)
        elif current_content:
            sections.append({
                "title": "",
                "level": 0,
                "content": "\n".join(current_content).strip(),
            })
        
        return sections
