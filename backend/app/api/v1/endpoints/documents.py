"""Document management endpoints."""

import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, BackgroundTasks

from app.config import settings
from app.core.dependencies import DbSession, CurrentUser
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentProcessingStatus,
    ChunkResponse,
)
from app.services.document_service import DocumentService
from app.ingestion.document_processor import DocumentProcessor
from app.chunking.chunker import Chunker, ChunkingStrategy
from app.embeddings.embedder import Embedder
from app.vectordb.vector_store import VectorStore

logger = structlog.get_logger()
router = APIRouter()


async def process_document_task(
    document_id: str,
    user_id: str,
    file_path: str,
    db_url: str,
):
    """Background task to process uploaded document."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create new database session for background task
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        doc_service = DocumentService(db)
        
        try:
            # Get document
            document = await doc_service.get_by_id(document_id, user_id)
            if not document:
                logger.error("Document not found for processing", document_id=document_id)
                return
            
            # Update status to processing
            await doc_service.update_status(document, "processing")
            await db.commit()
            
            # Step 1: Extract content
            processor = DocumentProcessor()
            content = await processor.process(file_path)
            
            # Update page count
            await doc_service.update_status(
                document,
                "processing",
                page_count=content.page_count,
            )
            await db.commit()
            
            # Step 2: Chunk content
            chunker = Chunker.create(
                strategy=ChunkingStrategy.RECURSIVE,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            
            if content.pages:
                chunks = chunker.chunk_with_pages(content.pages, content.metadata)
            else:
                chunks = chunker.chunk(content.text, content.metadata)
            
            # Step 3: Save chunks to database
            chunk_dicts = [
                {
                    "content": chunk.content,
                    "page_number": chunk.metadata.get("page_number"),
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ]
            
            db_chunks = await doc_service.add_chunks(document_id, chunk_dicts)
            await db.commit()
            
            # Step 4: Generate embeddings
            embedder = Embedder.get_default()
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await embedder.embed_batch(chunk_texts)
            
            # Step 5: Store in vector database
            vector_store = await VectorStore.get_default()
            
            chunk_ids = [c.id for c in db_chunks]
            metadatas = [
                {
                    "document_id": document_id,
                    "document_name": document.original_filename,
                    "user_id": user_id,
                    "chunk_index": i,
                    "page_number": chunk.metadata.get("page_number"),
                    "file_type": document.file_type,
                }
                for i, chunk in enumerate(chunks)
            ]
            
            await vector_store.add(
                ids=chunk_ids,
                embeddings=embeddings,
                contents=chunk_texts,
                metadatas=metadatas,
            )
            
            # Update chunk embedding status
            await doc_service.update_chunk_embeddings(
                chunk_ids=chunk_ids,
                embedding_ids=chunk_ids,
            )
            
            # Update document status to completed
            await doc_service.update_status(
                document,
                "completed",
                chunk_count=len(chunks),
                embedding_count=len(embeddings),
            )
            await db.commit()
            
            logger.info(
                "Document processing completed",
                document_id=document_id,
                chunks=len(chunks),
            )
            
        except Exception as e:
            logger.error(
                "Document processing failed",
                document_id=document_id,
                error=str(e),
            )
            
            # Update status to failed
            document = await doc_service.get_by_id(document_id, user_id)
            if document:
                await doc_service.update_status(
                    document,
                    "failed",
                    error_message=str(e),
                )
                await db.commit()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    tags: str | None = Form(None),
):
    """Upload a document for processing."""
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {settings.allowed_extensions_list}",
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )
    
    # Save file
    doc_service = DocumentService(db)
    filename, file_path = await doc_service.save_uploaded_file(
        user_id=current_user.id,
        file_content=content,
        original_filename=file.filename,
    )
    
    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Create document record
    document = await doc_service.create(
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename,
        file_type=file_ext,
        file_size=len(content),
        file_path=file_path,
        title=title,
        description=description,
        tags=tag_list,
    )
    
    # Queue background processing
    background_tasks.add_task(
        process_document_task,
        document_id=document.id,
        user_id=current_user.id,
        file_path=file_path,
        db_url=settings.database_url,
    )
    
    logger.info(
        "Document uploaded",
        document_id=document.id,
        filename=file.filename,
        user_id=current_user.id,
    )
    
    return DocumentUploadResponse(
        id=document.id,
        filename=file.filename,
        status="pending",
        message="Document uploaded successfully. Processing started.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: DbSession,
    current_user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    file_type: str | None = None,
    search: str | None = None,
):
    """List all documents for the current user."""
    doc_service = DocumentService(db)
    
    return await doc_service.get_all(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        file_type=file_type,
        search=search,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific document."""
    doc_service = DocumentService(db)
    
    document = await doc_service.get_by_id(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/status", response_model=DocumentProcessingStatus)
async def get_document_status(
    document_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get document processing status."""
    doc_service = DocumentService(db)
    
    document = await doc_service.get_by_id(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Calculate progress
    progress = 0.0
    if document.status == "completed":
        progress = 100.0
    elif document.status == "processing":
        if document.chunk_count > 0 and document.embedding_count > 0:
            progress = 90.0
        elif document.chunk_count > 0:
            progress = 60.0
        elif document.page_count:
            progress = 30.0
        else:
            progress = 10.0
    elif document.status == "failed":
        progress = 0.0
    
    return DocumentProcessingStatus(
        id=document.id,
        status=document.status,
        progress=progress,
        chunk_count=document.chunk_count,
        embedding_count=document.embedding_count,
        error_message=document.error_message,
    )


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get all chunks for a document."""
    doc_service = DocumentService(db)
    
    chunks = await doc_service.get_chunks(document_id, current_user.id)
    
    return [ChunkResponse.model_validate(chunk) for chunk in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a document and all associated data."""
    doc_service = DocumentService(db)
    
    document = await doc_service.get_by_id(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Delete from vector store
    try:
        vector_store = await VectorStore.get_default()
        await vector_store.delete_by_metadata({"document_id": document_id})
    except Exception as e:
        logger.warning("Failed to delete from vector store", error=str(e))
    
    # Delete document (cascades to chunks)
    await doc_service.delete(document)
    
    logger.info("Document deleted", document_id=document_id, user_id=current_user.id)


@router.post("/{document_id}/reindex", response_model=DocumentUploadResponse)
async def reindex_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    """Re-process and re-index a document."""
    doc_service = DocumentService(db)
    
    document = await doc_service.get_by_id(document_id, current_user.id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Delete existing vectors
    try:
        vector_store = await VectorStore.get_default()
        await vector_store.delete_by_metadata({"document_id": document_id})
    except Exception as e:
        logger.warning("Failed to delete existing vectors", error=str(e))
    
    # Reset document status
    await doc_service.update_status(
        document,
        "pending",
        chunk_count=0,
        embedding_count=0,
        error_message=None,
    )
    
    # Queue reprocessing
    background_tasks.add_task(
        process_document_task,
        document_id=document.id,
        user_id=current_user.id,
        file_path=document.file_path,
        db_url=settings.database_url,
    )
    
    return DocumentUploadResponse(
        id=document.id,
        filename=document.original_filename,
        status="pending",
        message="Document re-indexing started.",
    )
