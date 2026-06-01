"""Chat service for conversation management."""

from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatHistoryResponse,
    SourceCitation,
)


class ChatService:
    """Service for chat-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_session(
        self, session_id: str, user_id: str
    ) -> ChatSession | None:
        """Get chat session by ID for a specific user."""
        result = await self.db.execute(
            select(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            .options(selectinload(ChatSession.messages))
        )
        return result.scalar_one_or_none()

    async def get_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ChatSessionListResponse:
        """Get all chat sessions for a user."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).where(ChatSession.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Get sessions with message count
        query = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()

        # Get message counts
        session_responses = []
        for session in sessions:
            msg_count = await self.db.execute(
                select(func.count()).where(ChatMessage.session_id == session.id)
            )
            session_responses.append(
                ChatSessionResponse(
                    id=session.id,
                    title=session.title,
                    message_count=msg_count.scalar() or 0,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
            )

        return ChatSessionListResponse(
            sessions=session_responses,
            total=total,
        )

    async def create_session(
        self,
        user_id: str,
        title: str = "New Chat",
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_session_title(
        self,
        session: ChatSession,
        title: str,
    ) -> ChatSession:
        """Update chat session title."""
        session.title = title
        session.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[SourceCitation] | None = None,
        confidence_score: float | None = None,
        retrieval_metadata: dict | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=[s.model_dump() for s in sources] if sources else None,
            confidence_score=confidence_score,
            retrieval_metadata=retrieval_metadata,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.db.add(message)
        
        # Update session timestamp
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """Get messages for a chat session."""
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_history(
        self,
        session_id: str,
        user_id: str,
    ) -> ChatHistoryResponse | None:
        """Get full chat history for a session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None

        messages = await self.get_messages(session_id)
        
        # Get message count
        msg_count = len(messages)

        return ChatHistoryResponse(
            session=ChatSessionResponse(
                id=session.id,
                title=session.title,
                message_count=msg_count,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            messages=[
                ChatMessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    sources=[
                        SourceCitation(**s) for s in msg.sources
                    ] if msg.sources else None,
                    confidence_score=msg.confidence_score,
                    created_at=msg.created_at,
                )
                for msg in messages
            ],
        )

    async def delete_session(self, session: ChatSession) -> None:
        """Delete a chat session and all its messages."""
        await self.db.delete(session)
        await self.db.flush()

    async def get_recent_context(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> list[dict]:
        """Get recent messages for context in RAG."""
        messages = await self.get_messages(session_id, limit=max_messages)
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def generate_title_from_message(self, message: str) -> str:
        """Generate a session title from the first message."""
        # Simple title generation - take first 50 chars
        title = message[:50].strip()
        if len(message) > 50:
            title += "..."
        return title
