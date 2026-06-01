"""Chat endpoints for RAG queries."""

import json
import time
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbSession, CurrentUser
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    SourceCitation,
)
from app.services.chat_service import ChatService
from app.rag.rag_pipeline import RAGPipeline

logger = structlog.get_logger()
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Send a message and get a RAG-powered response."""
    start_time = time.time()
    
    chat_service = ChatService(db)
    
    # Get or create session
    session = None
    conversation_history = None
    
    if request.session_id:
        session = await chat_service.get_session(request.session_id, current_user.id)
        if session:
            conversation_history = await chat_service.get_recent_context(
                session.id, max_messages=10
            )
    
    if not session:
        # Create new session
        title = await chat_service.generate_title_from_message(request.message)
        session = await chat_service.create_session(current_user.id, title)
    
    # Save user message
    await chat_service.add_message(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    
    # Execute RAG pipeline
    rag_pipeline = RAGPipeline(
        model=request.model,
        provider="openai",  # Default to OpenAI
    )
    
    try:
        response = await rag_pipeline.query(
            question=request.message,
            user_id=current_user.id,
            conversation_history=conversation_history,
            top_k=request.max_sources,
            temperature=request.temperature,
        )
    except Exception as e:
        logger.error("RAG query failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response",
        )
    
    # Save assistant message
    assistant_message = await chat_service.add_message(
        session_id=session.id,
        role="assistant",
        content=response.content,
        sources=response.sources if request.include_sources else None,
        confidence_score=response.confidence_score,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
    )
    
    return ChatResponse(
        message_id=assistant_message.id,
        session_id=session.id,
        content=response.content,
        sources=response.sources if request.include_sources else [],
        confidence_score=response.confidence_score,
        model_used=response.model_used,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
        response_time_ms=response.response_time_ms,
        created_at=assistant_message.created_at,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Send a message and get a streaming RAG-powered response."""
    chat_service = ChatService(db)
    
    # Get or create session
    session = None
    conversation_history = None
    
    if request.session_id:
        session = await chat_service.get_session(request.session_id, current_user.id)
        if session:
            conversation_history = await chat_service.get_recent_context(
                session.id, max_messages=10
            )
    
    if not session:
        title = await chat_service.generate_title_from_message(request.message)
        session = await chat_service.create_session(current_user.id, title)
    
    # Save user message
    await chat_service.add_message(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    
    async def generate() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        rag_pipeline = RAGPipeline(
            model=request.model,
            provider="openai",
        )
        
        full_content = ""
        sources = []
        confidence_score = 0.0
        
        try:
            async for chunk in rag_pipeline.query_stream(
                question=request.message,
                user_id=current_user.id,
                conversation_history=conversation_history,
                top_k=request.max_sources,
                temperature=request.temperature,
            ):
                if chunk["type"] == "content":
                    full_content += chunk["content"]
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk["type"] == "source":
                    sources.append(SourceCitation(**chunk["source"]))
                    if request.include_sources:
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk["type"] == "done":
                    confidence_score = chunk.get("confidence_score", 0.0)
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            # Save assistant message after streaming completes
            await chat_service.add_message(
                session_id=session.id,
                role="assistant",
                content=full_content,
                sources=sources if request.include_sources else None,
                confidence_score=confidence_score,
            )
            
        except Exception as e:
            logger.error("Streaming RAG query failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session.id,
        },
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: DbSession,
    current_user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
):
    """List all chat sessions for the current user."""
    chat_service = ChatService(db)
    
    return await chat_service.get_sessions(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get chat history for a specific session."""
    chat_service = ChatService(db)
    
    history = await chat_service.get_history(session_id, current_user.id)
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    return history


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    title: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update chat session title."""
    chat_service = ChatService(db)
    
    session = await chat_service.get_session(session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    updated_session = await chat_service.update_session_title(session, title)
    
    # Get message count
    messages = await chat_service.get_messages(session_id)
    
    return ChatSessionResponse(
        id=updated_session.id,
        title=updated_session.title,
        message_count=len(messages),
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a chat session."""
    chat_service = ChatService(db)
    
    session = await chat_service.get_session(session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    await chat_service.delete_session(session)
    
    logger.info("Chat session deleted", session_id=session_id, user_id=current_user.id)
