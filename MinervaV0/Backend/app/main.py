from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import documents, stories, users, chat
import os

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered learning app that transforms documents into interactive story-based experiences",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (for production)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1"]  # Configure for production
    )

# Create upload directory if it doesn't exist
os.makedirs(settings.upload_dir, exist_ok=True)

# Mount static files for uploaded documents
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include API routers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(stories.router, prefix="/api/v1/stories", tags=["stories"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "API documentation disabled in production"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}