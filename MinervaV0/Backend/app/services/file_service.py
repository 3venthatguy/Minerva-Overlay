import os
import uuid
import aiofiles
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import hashlib


class FileService:
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'}
    
    async def save_upload_file(self, upload_file: UploadFile, user_id: int) -> dict:
        """Save uploaded file and return file information"""
        
        # Validate file
        self._validate_file(upload_file)
        
        # Generate unique filename
        file_extension = os.path.splitext(upload_file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create user-specific directory
        user_dir = os.path.join(self.upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        file_path = os.path.join(user_dir, unique_filename)
        
        # Save file
        content = await upload_file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Calculate file hash for deduplication
        file_hash = hashlib.md5(content).hexdigest()
        
        return {
            "filename": unique_filename,
            "original_filename": upload_file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "file_type": file_extension[1:],  # Remove the dot
            "file_hash": file_hash,
            "content_type": upload_file.content_type
        }
    
    def _validate_file(self, upload_file: UploadFile) -> None:
        """Validate uploaded file"""
        
        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        file_extension = os.path.splitext(upload_file.filename)[1].lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not supported. Allowed types: {', '.join(self.allowed_extensions)}"
            )
        
        # Check file size (if we can)
        if hasattr(upload_file, 'size') and upload_file.size:
            if upload_file.size > self.max_file_size:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File size {upload_file.size} exceeds maximum allowed size {self.max_file_size}"
                )
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """Get URL for accessing uploaded file"""
        # Convert absolute path to relative URL
        relative_path = os.path.relpath(file_path, self.upload_dir)
        return f"/uploads/{relative_path}"


file_service = FileService()