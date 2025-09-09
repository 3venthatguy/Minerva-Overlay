from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    
    # Learning preferences and personality traits
    learning_style = Column(String(50), default="visual")  # visual, auditory, kinesthetic, reading
    personality_traits = Column(JSON, default={})  # Stores personality assessment results
    interests = Column(JSON, default=[])  # User's interests and subjects
    skill_level = Column(String(20), default="beginner")  # beginner, intermediate, advanced
    preferred_story_genres = Column(JSON, default=[])  # adventure, mystery, sci-fi, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    
    # Conversational memory for current session
    conversation_history = Column(JSON, default=[])
    current_story_context = Column(JSON, default={})
    learning_progress = Column(JSON, default={})
    personality_adaptations = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)