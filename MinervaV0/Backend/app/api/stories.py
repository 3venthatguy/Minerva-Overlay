from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User, UserSession
from app.models.story import StoryTemplate, GeneratedStory, StoryProgress
from app.services.story_engine import story_engine
from app.services.memory_service import memory_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class StoryGenerationRequest(BaseModel):
    document_id: int
    user_id: int
    session_token: str
    preferences: Optional[Dict[str, Any]] = None


class StoryResponse(BaseModel):
    id: int
    title: str
    synopsis: str
    user_character: Dict[str, Any]
    story_structure: Dict[str, Any]
    current_progress: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True


class StoryPhaseResponse(BaseModel):
    phase_index: int
    phase_title: str
    narrative: str
    key_moments: List[str]
    learning_checkpoints: List[Dict[str, Any]]
    challenges: List[str]
    outcomes: List[str]
    decision_points: List[Dict[str, Any]]
    completion_status: str  # not_started, in_progress, completed


class DecisionRequest(BaseModel):
    story_id: int
    session_token: str
    decision_point_id: str
    selected_option: int
    user_reasoning: Optional[str] = None


class KnowledgeCheckRequest(BaseModel):
    story_id: int
    session_token: str
    question_id: str
    selected_answer: int
    confidence_level: Optional[int] = None


class ProgressUpdate(BaseModel):
    story_id: int
    session_token: str
    phase_completed: Optional[int] = None
    time_spent: Optional[int] = None  # in seconds
    engagement_metrics: Optional[Dict[str, Any]] = None


async def generate_story_background_task(
    story_id: int,
    document_id: int,
    user_id: int,
    session_token: str,
    preferences: Optional[Dict],
    db: Session
):
    """Background task to generate story content"""
    try:
        # Get required data
        document = db.query(Document).filter(Document.id == document_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        user_session = await memory_service.get_session(session_token, db)
        
        if not all([document, user, user_session]):
            logger.error(f"Missing required data for story generation: story_id={story_id}")
            return
        
        # Generate story using AI engine
        story_data = await story_engine.generate_personalized_story(
            document, user, user_session, preferences
        )
        
        # Update story record with generated content
        story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
        if story:
            story.full_narrative = story_data["story_content"]["full_narrative"]
            story.story_structure = story_data["story_content"]["structure"]
            story.user_character = story_data["user_character"]
            story.personalization_factors = story_data["personalization_factors"]
            story.decision_points = story_data["interactive_elements"]["decision_points"]
            story.knowledge_checks = story_data["interactive_elements"]["knowledge_checks"]
            story.progress_milestones = story_data["interactive_elements"]["progress_milestones"]
            
            db.commit()
            
            # Update session context
            await memory_service.update_story_context(
                session_token,
                {
                    "current_story_id": story_id,
                    "story_framework": story_data["framework"]["name"],
                    "user_character": story_data["user_character"],
                    "generation_timestamp": datetime.utcnow().isoformat()
                },
                db
            )
            
            logger.info(f"Successfully generated story content for story_id={story_id}")
        
    except Exception as e:
        logger.error(f"Error generating story content: {str(e)}")
        # Update story with error status
        story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
        if story:
            story.generation_parameters = {"error": str(e), "status": "failed"}
            db.commit()


@router.post("/generate", response_model=StoryResponse)
async def generate_story(
    request: StoryGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate a personalized story from a document"""
    
    # Validate document exists and belongs to user
    document = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == request.user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.processing_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready for story generation. Status: {document.processing_status}"
        )
    
    # Validate user session
    user_session = await memory_service.get_session(request.session_token, db)
    if not user_session or user_session.user_id != request.user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Create story record
    story = GeneratedStory(
        user_id=request.user_id,
        document_id=request.document_id,
        template_id=1,  # Default template for now
        session_id=request.session_token,
        title="Generating your personalized story...",
        synopsis="Your story is being created based on the uploaded document and your preferences.",
        full_narrative="Story content is being generated...",
        story_structure={"status": "generating"},
        user_character={"status": "generating"},
        generation_parameters=request.preferences or {}
    )
    
    db.add(story)
    db.commit()
    db.refresh(story)
    
    # Create initial progress record
    progress = StoryProgress(
        user_id=request.user_id,
        story_id=story.id,
        session_id=request.session_token,
        current_chapter=0,
        current_scene=0,
        completion_percentage=0.0
    )
    
    db.add(progress)
    db.commit()
    
    # Start background story generation
    background_tasks.add_task(
        generate_story_background_task,
        story.id,
        request.document_id,
        request.user_id,
        request.session_token,
        request.preferences,
        db
    )
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        synopsis=story.synopsis,
        user_character=story.user_character,
        story_structure=story.story_structure,
        current_progress={
            "completion_percentage": 0.0,
            "current_phase": 0,
            "status": "generating"
        },
        created_at=story.created_at.isoformat()
    )


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get story details"""
    
    story = db.query(GeneratedStory).filter(
        GeneratedStory.id == story_id,
        GeneratedStory.user_id == user_id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get progress
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == user_id
    ).first()
    
    current_progress = {
        "completion_percentage": progress.completion_percentage if progress else 0.0,
        "current_phase": progress.current_chapter if progress else 0,
        "status": "completed" if story.full_narrative != "Story content is being generated..." else "generating"
    }
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        synopsis=story.synopsis,
        user_character=story.user_character,
        story_structure=story.story_structure,
        current_progress=current_progress,
        created_at=story.created_at.isoformat()
    )


@router.get("/{story_id}/phases/{phase_index}", response_model=StoryPhaseResponse)
async def get_story_phase(
    story_id: int,
    phase_index: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get specific story phase content"""
    
    story = db.query(GeneratedStory).filter(
        GeneratedStory.id == story_id,
        GeneratedStory.user_id == user_id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get phase from story structure
    story_structure = story.story_structure or {}
    phases = story_structure.get("phases", [])
    
    if phase_index >= len(phases):
        raise HTTPException(status_code=404, detail="Phase not found")
    
    phase_data = phases[phase_index]
    
    # Get decision points for this phase
    decision_points = [
        dp for dp in (story.decision_points or [])
        if dp.get("phase_index") == phase_index
    ]
    
    # Get progress
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == user_id
    ).first()
    
    completion_status = "not_started"
    if progress:
        if progress.current_chapter > phase_index:
            completion_status = "completed"
        elif progress.current_chapter == phase_index:
            completion_status = "in_progress"
    
    return StoryPhaseResponse(
        phase_index=phase_index,
        phase_title=phase_data.get("phase_title", f"Phase {phase_index + 1}"),
        narrative=phase_data.get("narrative", ""),
        key_moments=phase_data.get("key_moments", []),
        learning_checkpoints=phase_data.get("learning_checkpoints", []),
        challenges=phase_data.get("challenges", []),
        outcomes=phase_data.get("outcomes", []),
        decision_points=decision_points,
        completion_status=completion_status
    )


@router.post("/{story_id}/decisions")
async def make_decision(
    story_id: int,
    request: DecisionRequest,
    db: Session = Depends(get_db)
):
    """Record user decision and get consequences"""
    
    # Validate story and session
    story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    session = await memory_service.get_session(request.session_token, db)
    if not session or session.user_id != story.user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Find the decision point
    decision_points = story.decision_points or []
    decision_point = None
    
    for dp in decision_points:
        if dp.get("id") == request.decision_point_id:
            decision_point = dp
            break
    
    if not decision_point:
        raise HTTPException(status_code=404, detail="Decision point not found")
    
    # Validate selected option
    options = decision_point.get("options", [])
    if request.selected_option >= len(options):
        raise HTTPException(status_code=400, detail="Invalid option selected")
    
    selected_option = options[request.selected_option]
    
    # Record decision in progress
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == story.user_id
    ).first()
    
    if progress:
        decisions_made = progress.decisions_made or []
        decisions_made.append({
            "decision_point_id": request.decision_point_id,
            "selected_option": request.selected_option,
            "option_text": selected_option.get("text"),
            "outcome": selected_option.get("outcome"),
            "user_reasoning": request.user_reasoning,
            "timestamp": datetime.utcnow().isoformat()
        })
        progress.decisions_made = decisions_made
        db.commit()
    
    # Add to conversation memory
    await memory_service.add_conversation_message(
        request.session_token,
        "user",
        f"Decision made: {selected_option.get('text')}",
        {
            "type": "decision",
            "decision_point_id": request.decision_point_id,
            "story_id": story_id,
            "outcome": selected_option.get("outcome")
        },
        db
    )
    
    return {
        "message": "Decision recorded successfully",
        "selected_option": selected_option,
        "consequence": f"Your choice leads to: {selected_option.get('outcome')}",
        "story_impact": decision_point.get("impact", "This decision affects your journey ahead.")
    }


@router.post("/{story_id}/knowledge-check")
async def submit_knowledge_check(
    story_id: int,
    request: KnowledgeCheckRequest,
    db: Session = Depends(get_db)
):
    """Submit answer to knowledge check question"""
    
    # Validate story and session
    story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    session = await memory_service.get_session(request.session_token, db)
    if not session or session.user_id != story.user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Find the knowledge check
    knowledge_checks = story.knowledge_checks or []
    knowledge_check = None
    
    for kc in knowledge_checks:
        if kc.get("id") == request.question_id:
            knowledge_check = kc
            break
    
    if not knowledge_check:
        raise HTTPException(status_code=404, detail="Knowledge check not found")
    
    # Check answer
    correct_answer = knowledge_check.get("correct_answer", 0)
    is_correct = request.selected_answer == correct_answer
    
    # Record result in progress
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == story.user_id
    ).first()
    
    if progress:
        check_results = progress.knowledge_check_results or []
        check_results.append({
            "question_id": request.question_id,
            "concept": knowledge_check.get("concept"),
            "selected_answer": request.selected_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "confidence_level": request.confidence_level,
            "timestamp": datetime.utcnow().isoformat()
        })
        progress.knowledge_check_results = check_results
        
        # Update concepts learned if correct
        if is_correct:
            concepts_learned = progress.concepts_learned or []
            concept = knowledge_check.get("concept")
            if concept and concept not in concepts_learned:
                concepts_learned.append(concept)
            progress.concepts_learned = concepts_learned
        
        db.commit()
    
    # Add to conversation memory
    await memory_service.add_conversation_message(
        request.session_token,
        "user",
        f"Knowledge check answer: {is_correct}",
        {
            "type": "knowledge_check",
            "question_id": request.question_id,
            "concept": knowledge_check.get("concept"),
            "is_correct": is_correct,
            "story_id": story_id
        },
        db
    )
    
    # Provide feedback
    if is_correct:
        feedback = knowledge_check.get("feedback_success", "Correct! Well done.")
    else:
        feedback = knowledge_check.get("feedback_retry", "Not quite right. Try thinking about it differently.")
    
    return {
        "is_correct": is_correct,
        "feedback": feedback,
        "concept_mastered": is_correct,
        "correct_answer_index": correct_answer,
        "explanation": knowledge_check.get("explanation", "")
    }


@router.post("/{story_id}/progress")
async def update_progress(
    story_id: int,
    request: ProgressUpdate,
    db: Session = Depends(get_db)
):
    """Update story progress"""
    
    # Validate story and session
    story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    session = await memory_service.get_session(request.session_token, db)
    if not session or session.user_id != story.user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Update progress
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == story.user_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")
    
    # Update fields
    if request.phase_completed is not None:
        progress.current_chapter = request.phase_completed
        
        # Calculate completion percentage
        story_structure = story.story_structure or {}
        total_phases = len(story_structure.get("phases", []))
        if total_phases > 0:
            progress.completion_percentage = (request.phase_completed / total_phases) * 100
    
    # Update engagement metrics
    if request.engagement_metrics:
        current_metrics = progress.engagement_metrics or {}
        current_metrics.update(request.engagement_metrics)
        progress.engagement_metrics = current_metrics
    
    # Add time spent
    if request.time_spent:
        current_metrics = progress.engagement_metrics or {}
        total_time = current_metrics.get("total_time_spent", 0)
        current_metrics["total_time_spent"] = total_time + request.time_spent
        current_metrics["last_session_time"] = request.time_spent
        progress.engagement_metrics = current_metrics
    
    progress.last_accessed = datetime.utcnow()
    db.commit()
    
    # Update learning progress in memory
    await memory_service.update_learning_progress(
        request.session_token,
        {
            "story_id": story_id,
            "completion_percentage": progress.completion_percentage,
            "current_phase": progress.current_chapter,
            "concepts_learned": progress.concepts_learned or [],
            "last_updated": datetime.utcnow().isoformat()
        },
        db
    )
    
    return {
        "message": "Progress updated successfully",
        "current_progress": {
            "completion_percentage": progress.completion_percentage,
            "current_phase": progress.current_chapter,
            "concepts_learned_count": len(progress.concepts_learned or []),
            "decisions_made_count": len(progress.decisions_made or [])
        }
    }


@router.get("/{story_id}/progress")
async def get_progress(
    story_id: int,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get detailed progress information"""
    
    progress = db.query(StoryProgress).filter(
        StoryProgress.story_id == story_id,
        StoryProgress.user_id == user_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
    
    return {
        "story_id": story_id,
        "completion_percentage": progress.completion_percentage,
        "current_chapter": progress.current_chapter,
        "current_scene": progress.current_scene,
        "concepts_learned": progress.concepts_learned or [],
        "skills_developed": progress.skills_developed or [],
        "decisions_made": progress.decisions_made or [],
        "knowledge_check_results": progress.knowledge_check_results or [],
        "engagement_metrics": progress.engagement_metrics or {},
        "areas_for_improvement": progress.areas_for_improvement or [],
        "last_accessed": progress.last_accessed.isoformat() if progress.last_accessed else None,
        "story_title": story.title if story else "Unknown Story",
        "achievements": generate_achievements(progress)
    }


@router.get("/user/{user_id}")
async def list_user_stories(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all stories for a user"""
    
    stories = db.query(GeneratedStory).filter(
        GeneratedStory.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    story_list = []
    for story in stories:
        progress = db.query(StoryProgress).filter(
            StoryProgress.story_id == story.id,
            StoryProgress.user_id == user_id
        ).first()
        
        story_list.append({
            "id": story.id,
            "title": story.title,
            "synopsis": story.synopsis,
            "created_at": story.created_at.isoformat(),
            "completion_percentage": progress.completion_percentage if progress else 0.0,
            "last_accessed": progress.last_accessed.isoformat() if progress and progress.last_accessed else None,
            "document_title": story.document.original_filename if story.document else "Unknown Document"
        })
    
    return {
        "stories": story_list,
        "total": len(story_list)
    }


def generate_achievements(progress: StoryProgress) -> List[Dict[str, Any]]:
    """Generate achievements based on progress"""
    
    achievements = []
    
    # Completion achievements
    if progress.completion_percentage >= 100:
        achievements.append({
            "type": "completion",
            "title": "Story Master",
            "description": "Completed the entire learning story",
            "icon": "🎓"
        })
    elif progress.completion_percentage >= 50:
        achievements.append({
            "type": "progress",
            "title": "Halfway Hero",
            "description": "Reached the halfway point",
            "icon": "⭐"
        })
    
    # Learning achievements
    concepts_learned = len(progress.concepts_learned or [])
    if concepts_learned >= 10:
        achievements.append({
            "type": "learning",
            "title": "Knowledge Collector",
            "description": f"Mastered {concepts_learned} concepts",
            "icon": "🧠"
        })
    
    # Decision making achievements
    decisions_made = len(progress.decisions_made or [])
    if decisions_made >= 5:
        achievements.append({
            "type": "decision",
            "title": "Decision Maker",
            "description": f"Made {decisions_made} story decisions",
            "icon": "⚖️"
        })
    
    # Engagement achievements
    engagement_metrics = progress.engagement_metrics or {}
    total_time = engagement_metrics.get("total_time_spent", 0)
    if total_time >= 3600:  # 1 hour
        achievements.append({
            "type": "engagement",
            "title": "Dedicated Learner",
            "description": "Spent over an hour learning",
            "icon": "⏰"
        })
    
    return achievements