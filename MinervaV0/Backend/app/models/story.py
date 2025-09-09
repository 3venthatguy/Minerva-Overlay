from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class StoryTemplate(Base):
    __tablename__ = "story_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    genre = Column(String(50), nullable=False)  # adventure, mystery, sci-fi, historical, etc.
    description = Column(Text, nullable=False)
    
    # Template structure
    narrative_framework = Column(JSON, nullable=False)  # Story structure template
    character_archetypes = Column(JSON, default=[])  # Available character types
    setting_options = Column(JSON, default=[])  # Possible story settings
    conflict_types = Column(JSON, default=[])  # Types of conflicts/challenges
    
    # Adaptation parameters
    difficulty_adaptable = Column(Boolean, default=True)
    personality_adaptable = Column(Boolean, default=True)
    subject_adaptable = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GeneratedStory(Base):
    __tablename__ = "generated_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    template_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Story content
    title = Column(String(200), nullable=False)
    synopsis = Column(Text, nullable=False)
    full_narrative = Column(Text, nullable=False)
    story_structure = Column(JSON, nullable=False)  # Chapters, scenes, etc.
    
    # User personalization
    user_character = Column(JSON, nullable=False)  # User's character in the story
    personalization_factors = Column(JSON, default={})  # What was adapted for the user
    learning_objectives_mapped = Column(JSON, default=[])  # How learning goals map to story
    
    # Interactive elements
    decision_points = Column(JSON, default=[])  # Points where user makes choices
    knowledge_checks = Column(JSON, default=[])  # Embedded learning assessments
    progress_milestones = Column(JSON, default=[])  # Story progress tracking
    
    # Generation metadata
    generation_prompt = Column(Text, nullable=True)
    ai_model_used = Column(String(50), default="gpt-4")
    generation_parameters = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StoryProgress(Base):
    __tablename__ = "story_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    story_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Progress tracking
    current_chapter = Column(Integer, default=0)
    current_scene = Column(Integer, default=0)
    completion_percentage = Column(Float, default=0.0)
    
    # User interactions
    decisions_made = Column(JSON, default=[])  # User's choices throughout the story
    knowledge_check_results = Column(JSON, default=[])  # Assessment results
    engagement_metrics = Column(JSON, default={})  # Time spent, reactions, etc.
    
    # Learning outcomes
    concepts_learned = Column(JSON, default=[])  # Concepts the user has mastered
    skills_developed = Column(JSON, default=[])  # Skills gained through the story
    areas_for_improvement = Column(JSON, default=[])  # Areas needing more work
    
    last_accessed = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())