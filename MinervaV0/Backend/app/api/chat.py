from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserSession
from app.models.story import GeneratedStory, StoryProgress
from app.services.memory_service import memory_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    context_type: Optional[str] = "general"  # general, story, learning
    story_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    content: str
    response_type: str  # response, guidance, encouragement, explanation
    suggestions: Optional[List[str]] = None
    learning_insights: Optional[Dict[str, Any]] = None
    story_progression: Optional[Dict[str, Any]] = None


class ConversationHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    total_count: int
    session_info: Dict[str, Any]


class ChatEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_contextual_response(
        self,
        message: str,
        user: User,
        session: UserSession,
        context_type: str = "general",
        story_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Generate contextual response based on user message and context"""
        
        # Build context for AI response
        context = await self._build_conversation_context(
            user, session, context_type, story_id, db
        )
        
        # Generate response using OpenAI
        response = await self._generate_ai_response(message, context)
        
        # Analyze and enhance response
        enhanced_response = await self._enhance_response(response, context, message)
        
        return enhanced_response
    
    async def _build_conversation_context(
        self,
        user: User,
        session: UserSession,
        context_type: str,
        story_id: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """Build comprehensive context for AI response generation"""
        
        context = {
            "user_profile": {
                "name": user.full_name or user.username,
                "learning_style": user.learning_style,
                "skill_level": user.skill_level,
                "interests": user.interests or [],
                "personality_traits": user.personality_traits.get("active_traits", {}) if user.personality_traits else {}
            },
            "session_context": {
                "conversation_history": session.conversation_history[-10:] if session.conversation_history else [],
                "learning_progress": session.learning_progress or {},
                "personality_adaptations": session.personality_adaptations or {},
                "current_story_context": session.current_story_context or {}
            },
            "context_type": context_type,
            "recommendations": await memory_service.get_personalized_recommendations(session.session_token, db)
        }
        
        # Add story-specific context if applicable
        if story_id and db:
            story = db.query(GeneratedStory).filter(GeneratedStory.id == story_id).first()
            if story:
                progress = db.query(StoryProgress).filter(
                    StoryProgress.story_id == story_id,
                    StoryProgress.user_id == user.id
                ).first()
                
                context["story_context"] = {
                    "title": story.title,
                    "synopsis": story.synopsis,
                    "user_character": story.user_character,
                    "current_progress": {
                        "completion_percentage": progress.completion_percentage if progress else 0,
                        "current_phase": progress.current_chapter if progress else 0,
                        "concepts_learned": progress.concepts_learned if progress else [],
                        "recent_decisions": (progress.decisions_made or [])[-3:] if progress else []
                    }
                }
        
        return context
    
    async def _generate_ai_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate AI response using OpenAI"""
        
        system_prompt = self._create_system_prompt(context)
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add recent conversation history
        conversation_history = context["session_context"]["conversation_history"]
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._generate_fallback_response(message, context)
    
    def _create_system_prompt(self, context: Dict[str, Any]) -> str:
        """Create system prompt for AI response generation"""
        
        user_profile = context["user_profile"]
        session_context = context["session_context"]
        context_type = context["context_type"]
        
        base_prompt = f"""
        You are Minerva, an AI learning companion that helps users learn through interactive storytelling. 
        You're talking with {user_profile['name']}, who has a {user_profile['learning_style']} learning style 
        and is at a {user_profile['skill_level']} skill level.
        
        User's interests: {', '.join(user_profile['interests']) if user_profile['interests'] else 'Not specified'}
        
        Personality traits: {user_profile['personality_traits']}
        
        Current context: {context_type}
        """
        
        if context_type == "story":
            story_context = context.get("story_context", {})
            base_prompt += f"""
            
            You're currently helping the user through their learning story: "{story_context.get('title', 'Unknown Story')}"
            
            Story synopsis: {story_context.get('synopsis', 'No synopsis available')}
            
            User's character in the story: {story_context.get('user_character', {})}
            
            Current progress: {story_context.get('current_progress', {})}
            
            Provide responses that:
            1. Stay in character as Minerva, their learning companion
            2. Reference their story progress and character when relevant
            3. Encourage learning through the narrative
            4. Adapt to their personality and learning style
            5. Provide helpful guidance without breaking the story immersion
            """
        
        elif context_type == "learning":
            learning_progress = session_context["learning_progress"]
            base_prompt += f"""
            
            Current learning progress: {learning_progress}
            
            Provide responses that:
            1. Focus on educational guidance and support
            2. Adapt explanations to their learning style
            3. Encourage continued learning
            4. Suggest relevant story-based learning approaches
            5. Reference their interests when possible
            """
        
        else:  # general context
            base_prompt += f"""
            
            Provide responses that:
            1. Are helpful and encouraging
            2. Suggest how they might use story-based learning
            3. Adapt to their communication style and preferences
            4. Offer relevant learning opportunities
            5. Be friendly and supportive
            """
        
        # Add personalization based on adaptations
        adaptations = session_context["personality_adaptations"]
        if adaptations:
            base_prompt += f"""
            
            Communication adaptations based on your interactions:
            - Communication preference: {adaptations.get('communication_preference', 'balanced')}
            - Engagement style: {adaptations.get('engagement_style', 'balanced')}
            - Emotional tone needed: {adaptations.get('emotional_tone', 'neutral')}
            - Inferred learning style: {adaptations.get('inferred_learning_style', 'unknown')}
            
            Adapt your response accordingly.
            """
        
        base_prompt += """
        
        Keep responses concise but helpful (2-4 sentences usually). Be encouraging and personable.
        """
        
        return base_prompt
    
    def _generate_fallback_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate fallback response when AI fails"""
        
        user_name = context["user_profile"]["name"]
        
        fallback_responses = [
            f"Hi {user_name}! I'm here to help you with your learning journey. What would you like to explore today?",
            f"That's an interesting question, {user_name}! Let me think about how we can turn that into a learning adventure.",
            f"I love your curiosity, {user_name}! Learning through stories makes everything more engaging.",
            f"Great question, {user_name}! I'm here to help guide you through your personalized learning experience."
        ]
        
        import random
        return random.choice(fallback_responses)
    
    async def _enhance_response(
        self,
        response: str,
        context: Dict[str, Any],
        original_message: str
    ) -> Dict[str, Any]:
        """Enhance response with additional features"""
        
        enhanced = {
            "content": response,
            "response_type": self._classify_response_type(response, original_message),
            "suggestions": self._generate_suggestions(context, original_message),
            "learning_insights": self._extract_learning_insights(context),
            "story_progression": self._get_story_progression_info(context)
        }
        
        return enhanced
    
    def _classify_response_type(self, response: str, original_message: str) -> str:
        """Classify the type of response"""
        
        response_lower = response.lower()
        message_lower = original_message.lower()
        
        if any(word in response_lower for word in ["great", "excellent", "well done", "amazing"]):
            return "encouragement"
        elif any(word in message_lower for word in ["how", "what", "why", "explain"]):
            return "explanation"
        elif any(word in response_lower for word in ["try", "consider", "maybe", "suggest"]):
            return "guidance"
        else:
            return "response"
    
    def _generate_suggestions(self, context: Dict[str, Any], message: str) -> List[str]:
        """Generate relevant suggestions for the user"""
        
        suggestions = []
        user_profile = context["user_profile"]
        context_type = context["context_type"]
        
        if context_type == "story":
            story_context = context.get("story_context", {})
            current_progress = story_context.get("current_progress", {})
            completion = current_progress.get("completion_percentage", 0)
            
            if completion < 25:
                suggestions.append("Continue with your story to unlock new learning concepts")
                suggestions.append("Make decisions that align with your character's strengths")
            elif completion < 75:
                suggestions.append("Reflect on what you've learned so far")
                suggestions.append("Try applying your new knowledge to solve story challenges")
            else:
                suggestions.append("You're almost finished! Keep going to complete your learning journey")
                suggestions.append("Consider how you'll apply what you've learned in real life")
        
        elif context_type == "learning":
            learning_style = user_profile["learning_style"]
            
            if learning_style == "visual":
                suggestions.append("Look for visual elements in your story that illustrate concepts")
                suggestions.append("Try creating mental images of what you're learning")
            elif learning_style == "auditory":
                suggestions.append("Read story dialogue aloud or discuss concepts with others")
                suggestions.append("Listen for audio cues and verbal explanations")
            elif learning_style == "kinesthetic":
                suggestions.append("Engage with interactive story elements and decision points")
                suggestions.append("Practice applying concepts through story activities")
        
        else:  # general
            suggestions.extend([
                "Upload a document to create your personalized learning story",
                "Explore different story genres that match your interests",
                "Complete your user profile for better personalization"
            ])
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _extract_learning_insights(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract learning insights from context"""
        
        insights = {}
        
        session_context = context["session_context"]
        learning_progress = session_context["learning_progress"]
        
        if learning_progress:
            insights["concepts_learned_count"] = len(learning_progress.get("concepts_learned", []))
            insights["current_learning_focus"] = learning_progress.get("current_learning_focus")
            insights["learning_streak"] = learning_progress.get("learning_streak", 0)
        
        # Story-specific insights
        if "story_context" in context:
            story_progress = context["story_context"]["current_progress"]
            insights["story_completion"] = story_progress.get("completion_percentage", 0)
            insights["recent_achievements"] = story_progress.get("recent_achievements", [])
        
        return insights
    
    def _get_story_progression_info(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get story progression information if applicable"""
        
        if "story_context" not in context:
            return None
        
        story_context = context["story_context"]
        current_progress = story_context["current_progress"]
        
        return {
            "current_phase": current_progress.get("current_phase", 0),
            "completion_percentage": current_progress.get("completion_percentage", 0),
            "next_milestone": self._get_next_milestone(current_progress),
            "recent_decisions": current_progress.get("recent_decisions", [])
        }
    
    def _get_next_milestone(self, progress: Dict[str, Any]) -> Optional[str]:
        """Get next milestone for the user"""
        
        completion = progress.get("completion_percentage", 0)
        
        if completion < 25:
            return "25% - First Quarter Complete"
        elif completion < 50:
            return "50% - Halfway Point"
        elif completion < 75:
            return "75% - Three Quarters Done"
        elif completion < 100:
            return "100% - Story Complete!"
        else:
            return None


chat_engine = ChatEngine()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    user_id: int = 1,  # TODO: Get from authentication
    session_token: str = None,  # TODO: Get from authentication/headers
    db: Session = Depends(get_db)
):
    """Send a message to the AI learning companion"""
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create session
    if not session_token:
        session_token = await memory_service.create_session(user_id, db)
    
    session = await memory_service.get_session(session_token, db)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Add user message to conversation history
    await memory_service.add_conversation_message(
        session_token,
        "user",
        message.content,
        {
            "context_type": message.context_type,
            "story_id": message.story_id,
            "metadata": message.metadata
        },
        db
    )
    
    # Generate AI response
    response_data = await chat_engine.generate_contextual_response(
        message.content,
        user,
        session,
        message.context_type,
        message.story_id,
        db
    )
    
    # Add AI response to conversation history
    await memory_service.add_conversation_message(
        session_token,
        "assistant",
        response_data["content"],
        {
            "response_type": response_data["response_type"],
            "suggestions": response_data["suggestions"],
            "context_type": message.context_type
        },
        db
    )
    
    # Trigger personality analysis if enough messages
    await memory_service.analyze_personality_adaptations(session_token, db)
    
    return ChatResponse(**response_data)


@router.get("/conversation/{session_token}", response_model=ConversationHistoryResponse)
async def get_conversation(
    session_token: str,
    limit: Optional[int] = 50,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get conversation history for a session"""
    
    session = await memory_service.get_session(session_token, db)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await memory_service.get_conversation_history(session_token, limit, db)
    
    return ConversationHistoryResponse(
        messages=messages,
        total_count=len(session.conversation_history or []),
        session_info={
            "session_token": session_token,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "learning_progress": session.learning_progress or {},
            "personality_adaptations": session.personality_adaptations or {}
        }
    )


@router.post("/story-chat/{story_id}")
async def story_chat(
    story_id: int,
    message: str,
    session_token: str,
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Chat specifically about a story"""
    
    # Validate story exists and belongs to user
    story = db.query(GeneratedStory).filter(
        GeneratedStory.id == story_id,
        GeneratedStory.user_id == user_id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Send message with story context
    chat_message = ChatMessage(
        content=message,
        context_type="story",
        story_id=story_id
    )
    
    return await send_message(chat_message, user_id, session_token, db)


@router.get("/suggestions/{session_token}")
async def get_chat_suggestions(
    session_token: str,
    context_type: str = "general",
    user_id: int = 1,  # TODO: Get from authentication
    db: Session = Depends(get_db)
):
    """Get contextual chat suggestions"""
    
    session = await memory_service.get_session(session_token, db)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    context = await chat_engine._build_conversation_context(
        user, session, context_type, None, db
    )
    
    suggestions = chat_engine._generate_suggestions(context, "")
    
    # Add context-specific suggestions
    if context_type == "story":
        story_suggestions = [
            "How is my character developing in the story?",
            "What should I focus on learning next?",
            "Can you explain this concept in more detail?",
            "What are my options for the next decision?"
        ]
        suggestions.extend(story_suggestions)
    
    elif context_type == "learning":
        learning_suggestions = [
            "What's the best way to approach this topic?",
            "How can I apply what I've learned?",
            "Can you create a story to help me learn this?",
            "What are some practice exercises I can try?"
        ]
        suggestions.extend(learning_suggestions)
    
    else:  # general
        general_suggestions = [
            "How do I get started with Minerva?",
            "What types of documents can I upload?",
            "Can you help me choose a learning story?",
            "How does the personality adaptation work?"
        ]
        suggestions.extend(general_suggestions)
    
    return {
        "suggestions": suggestions[:8],  # Limit to 8 suggestions
        "context_type": context_type,
        "session_info": {
            "personality_adaptations": session.personality_adaptations or {},
            "learning_progress": session.learning_progress or {}
        }
    }