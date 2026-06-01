"""Analytics schemas."""

from datetime import datetime
from pydantic import BaseModel


class DailyStats(BaseModel):
    """Daily statistics schema."""
    
    date: str
    queries: int
    documents_uploaded: int
    tokens_used: int


class TopicStats(BaseModel):
    """Topic statistics schema."""
    
    topic: str
    count: int
    percentage: float


class AnalyticsSummary(BaseModel):
    """Analytics summary schema."""
    
    total_documents: int
    total_chunks: int
    total_queries: int
    total_tokens_used: int
    avg_response_time_ms: float
    avg_confidence_score: float
    documents_this_week: int
    queries_this_week: int


class AnalyticsResponse(BaseModel):
    """Analytics response schema."""
    
    summary: AnalyticsSummary
    daily_stats: list[DailyStats]
    top_topics: list[TopicStats]
    recent_queries: list[str]


class UsageMetrics(BaseModel):
    """Usage metrics schema."""
    
    period: str
    documents_uploaded: int
    queries_made: int
    tokens_used: int
    avg_response_time_ms: float
    retrieval_accuracy: float


class PerformanceMetrics(BaseModel):
    """Performance metrics schema."""
    
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    avg_total_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float


class KnowledgeGraphNode(BaseModel):
    """Knowledge graph node schema."""
    
    id: str
    label: str
    type: str  # document, topic, concept
    size: int
    metadata: dict | None = None


class KnowledgeGraphEdge(BaseModel):
    """Knowledge graph edge schema."""
    
    source: str
    target: str
    weight: float
    relationship: str


class KnowledgeGraphResponse(BaseModel):
    """Knowledge graph response schema."""
    
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
