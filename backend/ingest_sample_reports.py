import os
import shutil
import uuid
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.document_service import DocumentService
from app.api.v1.endpoints.documents import process_document_task

# Configuration
USER_ID = "991bd867-a5dc-4010-ab28-fab2b902eb41" # demo1780804851699@knowledgepilot.demo
REPORTS_DIR = Path("C:/Users/sasir/Downloads/reports")
UPLOADS_DIR = Path("data/uploads") / USER_ID

async def ingest_file(filename: str):
    source_path = REPORTS_DIR / filename
    if not source_path.exists():
        print(f"Source report not found: {source_path}")
        return
        
    print(f"Ingesting report: {filename}...")
    
    # Create uploads directory if not exists
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename for upload storage
    file_ext = source_path.suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    dest_path = UPLOADS_DIR / unique_filename
    
    # Copy file to uploads directory
    shutil.copy(source_path, dest_path)
    file_size = os.path.getsize(dest_path)
    
    # Create DB session
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        doc_service = DocumentService(db)
        
        # Create document record
        title = filename.replace(".pdf", "").replace("-", " ")
        document = await doc_service.create(
            user_id=USER_ID,
            filename=unique_filename,
            original_filename=filename,
            file_type="pdf",
            file_size=file_size,
            file_path=str(dest_path),
            title=title,
            description=f"Sample report: {title}",
            tags=["sample", "report", "financial"],
        )
        await db.commit()
        document_id = document.id
        print(f"Created DB record with ID: {document_id}")
        
    # Trigger background task to process document
    print(f"Processing and chunking document...")
    await process_document_task(
        document_id=document_id,
        user_id=USER_ID,
        file_path=str(dest_path),
        db_url=settings.database_url
    )
    print(f"Successfully processed: {filename}\n")

async def main():
    files_to_ingest = [
        "Q1 FY27 Press Release.pdf",
        "Q1 FY27 Financial Tables.pdf"
    ]
    for file in files_to_ingest:
        await ingest_file(file)

if __name__ == "__main__":
    asyncio.run(main())
