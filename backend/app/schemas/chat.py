"""Chat schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """Source citation schema."""
    
    document_id: str
    document_name: str
    chunk_id: str
    content: str
    page_number: int | None = None
    relevance_score: float = Field(ge=0, le=1)


class ChatRequest(BaseModel):
    """Chat request schema."""
    
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = None
    include_sources: bool = True
    max_sources: int = Field(default=5, ge=1, le=10)
    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str | None = None


class ChatResponse(BaseModel):
    """Chat response schema."""
    
    message_id: str
    session_id: str
    content: str
    sources: list[SourceCitation]
    confidence_score: float = Field(ge=0, le=1)
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time_ms: int
    created_at: datetime


class ChatMessageResponse(BaseModel):
    """Chat message response schema."""
    
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    sources: list[SourceCitation] | None = None
    confidence_score: float | None = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""
    
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    """Chat session list response schema."""
    
    sessions: list[ChatSessionResponse]
    total: int


class ChatHistoryResponse(BaseModel):
    """Chat history response schema."""
    
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class StreamingChatChunk(BaseModel):
    """Streaming chat chunk schema."""
    
    type: Literal["content", "source", "done", "error"]
    content: str | None = None
    source: SourceCitation | None = None
    confidence_score: float | None = None
    error: str | None = None
