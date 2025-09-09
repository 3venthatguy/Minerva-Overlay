from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.services.file_service import file_service
from app.services.content_processor import content_processor
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    processing_status: str
    difficulty_level: Optional[str] = None
    estimated_reading_time: Optional[int] = None
    key_concepts: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None
    created_at: str
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


async def process_document_content(document_id: int, file_path: str, file_type: str, db: Session):
    """Background task to process document content"""
    try:
        # Update status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return
        
        document.processing_status = "processing"
        db.commit()
        
        # Extract and process content
        content_data = await content_processor.extract_content(file_path, file_type)
        
        # Update document with processed content
        document.raw_content = content_data["raw_content"]
        document.processed_content = content_data["processed_content"]
        document.content_structure = content_data["content_structure"]
        document.key_concepts = content_data["key_concepts"]
        document.learning_objectives = content_data["learning_objectives"]
        document.difficulty_level = content_data["difficulty_level"]
        document.estimated_reading_time = content_data["estimated_reading_time"]
        document.processing_status = "completed"
        
        db.commit()
        
        # Save document chunks
        for chunk_data in content_data["chunks"]:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_data["index"],
                content=chunk_data["content"],
                chunk_type="paragraph"
            )
            db.add(chunk)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        # Update document with error status
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = "error"
            document.processing_error = str(e)
            db.commit()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Upload and process a document"""
    
    try:
        # Save the uploaded file
        file_info = await file_service.save_upload_file(file, user_id)
        
        # Create document record
        document = Document(
            user_id=user_id,
            filename=file_info["filename"],
            original_filename=file_info["original_filename"],
            file_path=file_info["file_path"],
            file_type=file_info["file_type"],
            file_size=file_info["file_size"],
            processing_status="uploaded"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Start background processing
        background_tasks.add_task(
            process_document_content,
            document.id,
            file_info["file_path"],
            file_info["file_type"],
            db
        )
        
        return DocumentResponse.from_orm(document)
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user_id: int = 1,  # TODO: Get from authentication
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List user's documents"""
    
    documents = db.query(Document).filter(
        Document.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    total = db.query(Document).filter(Document.user_id == user_id).count()
    
    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get specific document details"""
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.from_orm(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Delete a document"""
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from storage
    await file_service.delete_file(document.file_path)
    
    # Delete document chunks
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # Delete document record
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get document content and structure"""
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.processing_status != "completed":
        raise HTTPException(
            status_code=202,
            detail=f"Document still processing. Status: {document.processing_status}"
        )
    
    # Get document chunks
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).all()
    
    return {
        "document": DocumentResponse.from_orm(document),
        "content": document.processed_content,
        "structure": document.content_structure,
        "chunks": [
            {
                "index": chunk.chunk_index,
                "content": chunk.content,
                "type": chunk.chunk_type
            }
            for chunk in chunks
        ]
    }