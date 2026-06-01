"""Document schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Document creation schema."""
    
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class DocumentMetadata(BaseModel):
    """Document metadata schema."""
    
    title: str | None = None
    author: str | None = None
    creation_date: str | None = None
    page_count: int | None = None
    word_count: int | None = None


class DocumentResponse(BaseModel):
    """Document response schema."""
    
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    title: str | None
    author: str | None
    description: str | None
    tags: list[str] | None
    status: Literal["pending", "processing", "completed", "failed"]
    page_count: int | None
    chunk_count: int
    embedding_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None
    
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Document list response schema."""
    
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""
    
    id: str
    filename: str
    status: str
    message: str


class DocumentProcessingStatus(BaseModel):
    """Document processing status schema."""
    
    id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: float = Field(ge=0, le=100)
    chunk_count: int
    embedding_count: int
    error_message: str | None = None


class ChunkResponse(BaseModel):
    """Chunk response schema."""
    
    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: int | None
    metadata: dict | None
    
    model_config = {"from_attributes": True}
