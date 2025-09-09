from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    file_size = Column(Integer, nullable=False)
    
    # Content extraction results
    raw_content = Column(Text, nullable=True)
    processed_content = Column(Text, nullable=True)
    content_structure = Column(JSON, default={})  # headings, sections, etc.
    key_concepts = Column(JSON, default=[])  # extracted key concepts
    learning_objectives = Column(JSON, default=[])  # identified learning objectives
    difficulty_level = Column(String(20), default="medium")
    estimated_reading_time = Column(Integer, default=0)  # in minutes
    
    # Processing status
    processing_status = Column(String(20), default="uploaded")  # uploaded, processing, completed, error
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_type = Column(String(50), default="paragraph")  # paragraph, heading, list, etc.
    
    # Semantic information
    embedding = Column(JSON, nullable=True)  # Vector embedding for semantic search
    concepts = Column(JSON, default=[])  # Key concepts in this chunk
    importance_score = Column(Float, default=0.0)  # Importance for learning
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())