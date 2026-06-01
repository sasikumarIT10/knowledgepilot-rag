"""Document service for file management and processing."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Document, Chunk
from app.schemas.document import DocumentListResponse, DocumentResponse


class DocumentService:
    """Service for document-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = Path("./data/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def get_by_id(
        self, document_id: str, user_id: str
    ) -> Document | None:
        """Get document by ID for a specific user."""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
            .options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        file_type: str | None = None,
        search: str | None = None,
    ) -> DocumentListResponse:
        """Get all documents for a user with pagination and filters."""
        query = select(Document).where(Document.user_id == user_id)

        if status:
            query = query.where(Document.status == status)
        
        if file_type:
            query = query.where(Document.file_type == file_type)
        
        if search:
            query = query.where(
                Document.original_filename.ilike(f"%{search}%")
                | Document.title.ilike(f"%{search}%")
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(Document.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def create(
        self,
        user_id: str,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        file_path: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Document:
        """Create a new document record."""
        document = Document(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            title=title or original_filename,
            description=description,
            tags=tags,
            status="pending",
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def save_uploaded_file(
        self,
        user_id: str,
        file_content: bytes,
        original_filename: str,
    ) -> tuple[str, str]:
        """Save uploaded file to disk and return (filename, file_path)."""
        # Create user directory
        user_dir = self.upload_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_ext = Path(original_filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = user_dir / unique_filename

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)

        return unique_filename, str(file_path)

    async def update_status(
        self,
        document: Document,
        status: str,
        error_message: str | None = None,
        chunk_count: int | None = None,
        embedding_count: int | None = None,
        page_count: int | None = None,
    ) -> Document:
        """Update document processing status."""
        document.status = status
        
        if error_message is not None:
            document.error_message = error_message
        
        if chunk_count is not None:
            document.chunk_count = chunk_count
        
        if embedding_count is not None:
            document.embedding_count = embedding_count
        
        if page_count is not None:
            document.page_count = page_count
        
        if status == "completed":
            document.processed_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def add_chunks(
        self,
        document_id: str,
        chunks: list[dict],
    ) -> list[Chunk]:
        """Add chunks to a document."""
        chunk_objects = []
        
        for i, chunk_data in enumerate(chunks):
            chunk = Chunk(
                document_id=document_id,
                content=chunk_data["content"],
                chunk_index=i,
                page_number=chunk_data.get("page_number"),
                start_char=chunk_data.get("start_char"),
                end_char=chunk_data.get("end_char"),
                metadata=chunk_data.get("metadata"),
            )
            self.db.add(chunk)
            chunk_objects.append(chunk)
        
        await self.db.flush()
        return chunk_objects

    async def update_chunk_embeddings(
        self,
        chunk_ids: list[str],
        embedding_ids: list[str],
    ) -> None:
        """Update chunks with embedding IDs."""
        for chunk_id, embedding_id in zip(chunk_ids, embedding_ids):
            result = await self.db.execute(
                select(Chunk).where(Chunk.id == chunk_id)
            )
            chunk = result.scalar_one_or_none()
            if chunk:
                chunk.embedding_id = embedding_id
                chunk.is_embedded = True
        
        await self.db.flush()

    async def delete(self, document: Document) -> None:
        """Delete a document and its associated files."""
        # Delete file from disk
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database (cascades to chunks)
        await self.db.delete(document)
        await self.db.flush()

    async def get_chunks(
        self,
        document_id: str,
        user_id: str,
    ) -> list[Chunk]:
        """Get all chunks for a document."""
        # Verify document belongs to user
        doc = await self.get_by_id(document_id, user_id)
        if not doc:
            return []
        
        result = await self.db.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return list(result.scalars().all())

    async def get_stats(self, user_id: str) -> dict:
        """Get document statistics for a user."""
        # Total documents
        total_docs = await self.db.execute(
            select(func.count()).where(Document.user_id == user_id)
        )
        
        # Total chunks
        total_chunks = await self.db.execute(
            select(func.count())
            .select_from(Chunk)
            .join(Document)
            .where(Document.user_id == user_id)
        )
        
        # Documents by status
        status_counts = await self.db.execute(
            select(Document.status, func.count())
            .where(Document.user_id == user_id)
            .group_by(Document.status)
        )
        
        # Documents by type
        type_counts = await self.db.execute(
            select(Document.file_type, func.count())
            .where(Document.user_id == user_id)
            .group_by(Document.file_type)
        )
        
        return {
            "total_documents": total_docs.scalar() or 0,
            "total_chunks": total_chunks.scalar() or 0,
            "by_status": dict(status_counts.all()),
            "by_type": dict(type_counts.all()),
        }
