from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.models.user import User, UserSession
from app.services.memory_service import memory_service
from datetime import datetime

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    learning_style: Optional[str] = "visual"
    interests: Optional[List[str]] = []
    skill_level: Optional[str] = "beginner"
    preferred_story_genres: Optional[List[str]] = []


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    learning_style: Optional[str] = None
    interests: Optional[List[str]] = None
    skill_level: Optional[str] = None
    preferred_story_genres: Optional[List[str]] = None
    personality_traits: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    learning_style: Optional[str]
    interests: Optional[List[str]]
    skill_level: Optional[str]
    preferred_story_genres: Optional[List[str]]
    personality_traits: Optional[Dict[str, Any]]
    created_at: str
    
    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    session_token: str
    user_id: int
    conversation_count: int
    learning_progress: Dict[str, Any]
    personality_adaptations: Dict[str, Any]
    recommendations: Dict[str, Any]
    created_at: str
    last_activity: Optional[str]


class PersonalityUpdate(BaseModel):
    traits: Dict[str, Any]
    source: str = "user_input"  # user_input, conversation_analysis, assessment


@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user profile"""
    
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Hash password (in production, use proper password hashing)
    hashed_password = f"hashed_{user_data.password}"  # TODO: Implement proper hashing
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        learning_style=user_data.learning_style,
        interests=user_data.interests,
        skill_level=user_data.skill_level,
        preferred_story_genres=user_data.preferred_story_genres,
        personality_traits={}
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user profile"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Update user profile"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update provided fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.post("/{user_id}/sessions", response_model=SessionResponse)
async def create_session(user_id: int, db: Session = Depends(get_db)):
    """Create a new learning session for the user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create new session
    session_token = await memory_service.create_session(user_id, db)
    
    # Get session details
    session = await memory_service.get_session(session_token, db)
    
    return SessionResponse(
        session_token=session_token,
        user_id=user_id,
        conversation_count=0,
        learning_progress={},
        personality_adaptations={},
        recommendations={},
        created_at=session.created_at.isoformat(),
        last_activity=None
    )


@router.get("/{user_id}/sessions/{session_token}", response_model=SessionResponse)
async def get_session(user_id: int, session_token: str, db: Session = Depends(get_db)):
    """Get session details and memory"""
    
    session = await memory_service.get_session(session_token, db)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get personalized recommendations
    recommendations = await memory_service.get_personalized_recommendations(session_token, db)
    
    return SessionResponse(
        session_token=session_token,
        user_id=session.user_id,
        conversation_count=len(session.conversation_history or []),
        learning_progress=session.learning_progress or {},
        personality_adaptations=session.personality_adaptations or {},
        recommendations=recommendations,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat() if session.last_activity else None
    )


@router.get("/{user_id}/sessions/{session_token}/conversation")
async def get_conversation_history(
    user_id: int,
    session_token: str,
    limit: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """Get conversation history for a session"""
    
    session = await memory_service.get_session(session_token, db)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = await memory_service.get_conversation_history(session_token, limit, db)
    
    return {
        "conversation_history": history,
        "total_messages": len(session.conversation_history or []),
        "session_info": {
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat() if session.last_activity else None
        }
    }


@router.post("/{user_id}/personality")
async def update_personality_traits(
    user_id: int,
    personality_data: PersonalityUpdate,
    db: Session = Depends(get_db)
):
    """Update user's personality traits"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update personality traits
    current_traits = user.personality_traits or {}
    
    # Add metadata about the update
    update_entry = {
        "traits": personality_data.traits,
        "source": personality_data.source,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Store update history
    trait_history = current_traits.get("update_history", [])
    trait_history.append(update_entry)
    
    # Update current traits
    current_active_traits = current_traits.get("active_traits", {})
    current_active_traits.update(personality_data.traits)
    
    user.personality_traits = {
        "active_traits": current_active_traits,
        "update_history": trait_history[-10:],  # Keep last 10 updates
        "last_updated": datetime.utcnow().isoformat()
    }
    
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Personality traits updated successfully",
        "active_traits": current_active_traits,
        "update_source": personality_data.source
    }


@router.get("/{user_id}/personality")
async def get_personality_profile(user_id: int, db: Session = Depends(get_db)):
    """Get comprehensive personality profile"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    personality_data = user.personality_traits or {}
    
    return {
        "user_id": user_id,
        "active_traits": personality_data.get("active_traits", {}),
        "learning_style": user.learning_style,
        "skill_level": user.skill_level,
        "interests": user.interests or [],
        "preferred_story_genres": user.preferred_story_genres or [],
        "trait_sources": [
            entry.get("source") for entry in personality_data.get("update_history", [])
        ],
        "last_updated": personality_data.get("last_updated"),
        "profile_completeness": calculate_profile_completeness(user)
    }


@router.post("/{user_id}/sessions/{session_token}/analyze-personality")
async def analyze_session_personality(
    user_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Trigger personality analysis based on session interactions"""
    
    session = await memory_service.get_session(session_token, db)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Perform personality analysis
    adaptations = await memory_service.analyze_personality_adaptations(session_token, db)
    
    if not adaptations:
        return {
            "message": "Insufficient conversation data for personality analysis",
            "min_messages_required": memory_service.personality_analysis_threshold
        }
    
    # Update user's personality traits with insights
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        current_traits = user.personality_traits or {}
        
        # Add conversation-derived insights
        conversation_insights = {
            "communication_style": adaptations.get("communication_preference"),
            "engagement_pattern": adaptations.get("engagement_style"),
            "learning_pace": adaptations.get("pacing_preference"),
            "inferred_learning_style": adaptations.get("inferred_learning_style")
        }
        
        # Filter out None values
        conversation_insights = {k: v for k, v in conversation_insights.items() if v is not None}
        
        if conversation_insights:
            current_active_traits = current_traits.get("active_traits", {})
            current_active_traits.update(conversation_insights)
            
            user.personality_traits = {
                **current_traits,
                "active_traits": current_active_traits,
                "last_conversation_analysis": datetime.utcnow().isoformat(),
                "analysis_session": session_token
            }
            
            user.updated_at = datetime.utcnow()
            db.commit()
    
    return {
        "message": "Personality analysis completed",
        "adaptations_found": adaptations,
        "insights_applied": conversation_insights if 'conversation_insights' in locals() else {},
        "analysis_timestamp": adaptations.get("analysis_timestamp")
    }


@router.get("/{user_id}/learning-recommendations")
async def get_learning_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Get personalized learning recommendations based on user profile"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's most recent active session
    recent_session = db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).order_by(UserSession.last_activity.desc()).first()
    
    recommendations = {
        "story_preferences": generate_story_recommendations(user),
        "learning_approach": generate_learning_approach_recommendations(user),
        "content_preferences": generate_content_recommendations(user)
    }
    
    # Add session-based recommendations if available
    if recent_session:
        session_recommendations = await memory_service.get_personalized_recommendations(
            recent_session.session_token, db
        )
        recommendations["session_based"] = session_recommendations
    
    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "profile_basis": {
            "learning_style": user.learning_style,
            "skill_level": user.skill_level,
            "interests": user.interests,
            "personality_traits": user.personality_traits.get("active_traits", {}) if user.personality_traits else {}
        },
        "generated_at": datetime.utcnow().isoformat()
    }


def calculate_profile_completeness(user: User) -> Dict[str, Any]:
    """Calculate how complete the user's profile is"""
    
    total_fields = 8
    completed_fields = 0
    missing_fields = []
    
    # Check core fields
    if user.full_name:
        completed_fields += 1
    else:
        missing_fields.append("full_name")
    
    if user.learning_style:
        completed_fields += 1
    else:
        missing_fields.append("learning_style")
    
    if user.skill_level:
        completed_fields += 1
    else:
        missing_fields.append("skill_level")
    
    if user.interests and len(user.interests) > 0:
        completed_fields += 1
    else:
        missing_fields.append("interests")
    
    if user.preferred_story_genres and len(user.preferred_story_genres) > 0:
        completed_fields += 1
    else:
        missing_fields.append("preferred_story_genres")
    
    # Check personality traits
    personality_traits = user.personality_traits or {}
    active_traits = personality_traits.get("active_traits", {})
    
    if len(active_traits) >= 3:
        completed_fields += 1
    else:
        missing_fields.append("personality_traits")
    
    # Check for conversation-based insights
    if personality_traits.get("last_conversation_analysis"):
        completed_fields += 1
    else:
        missing_fields.append("conversation_analysis")
    
    # Check for learning history
    if personality_traits.get("update_history"):
        completed_fields += 1
    else:
        missing_fields.append("learning_history")
    
    completeness_percentage = (completed_fields / total_fields) * 100
    
    return {
        "percentage": completeness_percentage,
        "completed_fields": completed_fields,
        "total_fields": total_fields,
        "missing_fields": missing_fields,
        "completeness_level": get_completeness_level(completeness_percentage)
    }


def get_completeness_level(percentage: float) -> str:
    """Get qualitative completeness level"""
    if percentage >= 90:
        return "excellent"
    elif percentage >= 70:
        return "good"
    elif percentage >= 50:
        return "moderate"
    elif percentage >= 30:
        return "basic"
    else:
        return "minimal"


def generate_story_recommendations(user: User) -> Dict[str, Any]:
    """Generate story-related recommendations"""
    
    preferred_genres = user.preferred_story_genres or []
    personality_traits = user.personality_traits.get("active_traits", {}) if user.personality_traits else {}
    
    recommendations = {
        "recommended_genres": preferred_genres if preferred_genres else ["adventure", "mystery"],
        "narrative_complexity": "medium",
        "character_type": "explorer"
    }
    
    # Adjust based on skill level
    if user.skill_level == "beginner":
        recommendations["narrative_complexity"] = "simple"
        recommendations["pacing"] = "slow"
    elif user.skill_level == "advanced":
        recommendations["narrative_complexity"] = "complex"
        recommendations["pacing"] = "fast"
    
    # Adjust based on personality
    if personality_traits.get("analytical"):
        recommendations["recommended_genres"].append("mystery")
        recommendations["character_type"] = "scholar"
    
    if personality_traits.get("creative"):
        recommendations["recommended_genres"].append("fantasy")
        recommendations["character_type"] = "innovator"
    
    return recommendations


def generate_learning_approach_recommendations(user: User) -> Dict[str, Any]:
    """Generate learning approach recommendations"""
    
    learning_style = user.learning_style or "visual"
    personality_traits = user.personality_traits.get("active_traits", {}) if user.personality_traits else {}
    
    recommendations = {
        "primary_approach": learning_style,
        "content_format": "mixed",
        "interaction_frequency": "moderate"
    }
    
    # Adjust based on learning style
    if learning_style == "visual":
        recommendations["content_format"] = "visual_heavy"
        recommendations["recommended_elements"] = ["diagrams", "charts", "illustrations"]
    elif learning_style == "auditory":
        recommendations["content_format"] = "narrative_heavy"
        recommendations["recommended_elements"] = ["discussions", "explanations", "verbal reasoning"]
    elif learning_style == "kinesthetic":
        recommendations["content_format"] = "interactive"
        recommendations["recommended_elements"] = ["hands-on activities", "simulations", "practice exercises"]
    
    # Adjust based on personality
    if personality_traits.get("detail_oriented"):
        recommendations["explanation_depth"] = "detailed"
    elif personality_traits.get("big_picture_thinking"):
        recommendations["explanation_depth"] = "overview_focused"
    
    return recommendations


def generate_content_recommendations(user: User) -> Dict[str, Any]:
    """Generate content preference recommendations"""
    
    interests = user.interests or []
    skill_level = user.skill_level or "beginner"
    
    recommendations = {
        "content_difficulty": skill_level,
        "topic_areas": interests if interests else ["general knowledge"],
        "content_length": "medium"
    }
    
    # Adjust based on skill level
    if skill_level == "beginner":
        recommendations["content_length"] = "short"
        recommendations["explanation_style"] = "step_by_step"
    elif skill_level == "advanced":
        recommendations["content_length"] = "long"
        recommendations["explanation_style"] = "conceptual"
    
    # Add subject-specific recommendations
    if interests:
        recommendations["cross_subject_connections"] = True
        recommendations["real_world_applications"] = True
    
    return recommendations