"""Analytics endpoints."""

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter
from sqlalchemy import select, func

from app.core.dependencies import DbSession, CurrentUser
from app.db.models import Document, Chunk, ChatSession, ChatMessage, Analytics
from app.schemas.analytics import (
    AnalyticsResponse,
    AnalyticsSummary,
    DailyStats,
    TopicStats,
    KnowledgeGraphResponse,
    KnowledgeGraphNode,
    KnowledgeGraphEdge,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    db: DbSession,
    current_user: CurrentUser,
):
    """Get analytics dashboard data."""
    user_id = current_user.id
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    
    # Total documents
    total_docs_result = await db.execute(
        select(func.count()).where(Document.user_id == user_id)
    )
    total_documents = total_docs_result.scalar() or 0
    
    # Total chunks
    total_chunks_result = await db.execute(
        select(func.count())
        .select_from(Chunk)
        .join(Document)
        .where(Document.user_id == user_id)
    )
    total_chunks = total_chunks_result.scalar() or 0
    
    # Total queries (messages from user)
    total_queries_result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(ChatSession.user_id == user_id, ChatMessage.role == "user")
    )
    total_queries = total_queries_result.scalar() or 0
    
    # Total tokens used
    tokens_result = await db.execute(
        select(func.sum(ChatMessage.prompt_tokens + ChatMessage.completion_tokens))
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(ChatSession.user_id == user_id)
    )
    total_tokens_used = tokens_result.scalar() or 0
    
    # Average confidence score
    avg_confidence_result = await db.execute(
        select(func.avg(ChatMessage.confidence_score))
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.role == "assistant",
            ChatMessage.confidence_score.isnot(None),
        )
    )
    avg_confidence_score = avg_confidence_result.scalar() or 0.0
    
    # Documents this week
    docs_this_week_result = await db.execute(
        select(func.count()).where(
            Document.user_id == user_id,
            Document.created_at >= week_ago,
        )
    )
    documents_this_week = docs_this_week_result.scalar() or 0
    
    # Queries this week
    queries_this_week_result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= week_ago,
        )
    )
    queries_this_week = queries_this_week_result.scalar() or 0
    
    # Daily stats for last 7 days
    daily_stats = []
    for i in range(7):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Documents uploaded that day
        day_docs_result = await db.execute(
            select(func.count()).where(
                Document.user_id == user_id,
                Document.created_at >= day_start,
                Document.created_at < day_end,
            )
        )
        day_docs = day_docs_result.scalar() or 0
        
        # Queries that day
        day_queries_result = await db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .join(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.role == "user",
                ChatMessage.created_at >= day_start,
                ChatMessage.created_at < day_end,
            )
        )
        day_queries = day_queries_result.scalar() or 0
        
        # Tokens that day
        day_tokens_result = await db.execute(
            select(func.sum(ChatMessage.prompt_tokens + ChatMessage.completion_tokens))
            .select_from(ChatMessage)
            .join(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.created_at >= day_start,
                ChatMessage.created_at < day_end,
            )
        )
        day_tokens = day_tokens_result.scalar() or 0
        
        daily_stats.append(
            DailyStats(
                date=day_start.strftime("%Y-%m-%d"),
                queries=day_queries,
                documents_uploaded=day_docs,
                tokens_used=day_tokens,
            )
        )
    
    daily_stats.reverse()  # Oldest first
    
    # Top topics (based on document file types for now)
    file_types_result = await db.execute(
        select(Document.file_type, func.count())
        .where(Document.user_id == user_id)
        .group_by(Document.file_type)
        .order_by(func.count().desc())
        .limit(5)
    )
    file_types = file_types_result.all()
    
    top_topics = []
    for file_type, count in file_types:
        percentage = (count / total_documents * 100) if total_documents > 0 else 0
        top_topics.append(
            TopicStats(
                topic=file_type.upper(),
                count=count,
                percentage=round(percentage, 1),
            )
        )
    
    # Recent queries
    recent_queries_result = await db.execute(
        select(ChatMessage.content)
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(ChatSession.user_id == user_id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    recent_queries = [r[0][:100] for r in recent_queries_result.all()]
    
    return AnalyticsResponse(
        summary=AnalyticsSummary(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_queries=total_queries,
            total_tokens_used=total_tokens_used,
            avg_response_time_ms=0.0,  # Would need to track this
            avg_confidence_score=float(avg_confidence_score),
            documents_this_week=documents_this_week,
            queries_this_week=queries_this_week,
        ),
        daily_stats=daily_stats,
        top_topics=top_topics,
        recent_queries=recent_queries,
    )


@router.get("/knowledge-graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    db: DbSession,
    current_user: CurrentUser,
):
    """Get knowledge graph visualization data."""
    user_id = current_user.id
    
    # Get all documents
    docs_result = await db.execute(
        select(Document).where(
            Document.user_id == user_id,
            Document.status == "completed",
        )
    )
    documents = docs_result.scalars().all()
    
    nodes = []
    edges = []
    
    # Create document nodes
    for doc in documents:
        nodes.append(
            KnowledgeGraphNode(
                id=doc.id,
                label=doc.original_filename[:30],
                type="document",
                size=doc.chunk_count or 1,
                metadata={
                    "file_type": doc.file_type,
                    "chunks": doc.chunk_count,
                    "created_at": doc.created_at.isoformat(),
                },
            )
        )
    
    # Create file type topic nodes
    file_types = set(doc.file_type for doc in documents)
    for ft in file_types:
        ft_docs = [d for d in documents if d.file_type == ft]
        nodes.append(
            KnowledgeGraphNode(
                id=f"type_{ft}",
                label=ft.upper(),
                type="topic",
                size=len(ft_docs) * 2,
            )
        )
        
        # Connect documents to their type
        for doc in ft_docs:
            edges.append(
                KnowledgeGraphEdge(
                    source=doc.id,
                    target=f"type_{ft}",
                    weight=1.0,
                    relationship="belongs_to",
                )
            )
    
    # Create connections between documents with similar sizes (simple heuristic)
    for i, doc1 in enumerate(documents):
        for doc2 in documents[i + 1:]:
            if doc1.file_type == doc2.file_type:
                # Same type documents are related
                edges.append(
                    KnowledgeGraphEdge(
                        source=doc1.id,
                        target=doc2.id,
                        weight=0.5,
                        relationship="similar_type",
                    )
                )
    
    return KnowledgeGraphResponse(
        nodes=nodes,
        edges=edges,
    )
