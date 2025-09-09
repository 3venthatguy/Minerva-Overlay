import json
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.user import User, UserSession
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class ConversationalMemoryService:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.redis_client = None
        
        self.memory_retention_days = 30
        self.max_conversation_length = 100  # Max messages to keep in memory
        self.personality_analysis_threshold = 10  # Min messages before personality analysis
    
    async def create_session(self, user_id: int, db: Session) -> str:
        """Create a new user session with memory tracking"""
        
        session_token = self._generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Create database session record
        user_session = UserSession(
            user_id=user_id,
            session_token=session_token,
            conversation_history=[],
            current_story_context={},
            learning_progress={},
            personality_adaptations={},
            expires_at=expires_at
        )
        
        db.add(user_session)
        db.commit()
        db.refresh(user_session)
        
        # Initialize Redis cache if available
        if self.redis_client:
            await self._cache_session(session_token, user_session)
        
        return session_token
    
    async def get_session(self, session_token: str, db: Session) -> Optional[UserSession]:
        """Retrieve user session with memory"""
        
        # Try Redis cache first
        if self.redis_client:
            cached_session = await self._get_cached_session(session_token)
            if cached_session:
                return cached_session
        
        # Fallback to database
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if session and self.redis_client:
            # Cache for next time
            await self._cache_session(session_token, session)
        
        return session
    
    async def add_conversation_message(
        self,
        session_token: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        db: Session = None
    ) -> None:
        """Add a message to conversation history"""
        
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Update in database
        if db:
            session = await self.get_session(session_token, db)
            if session:
                conversation_history = session.conversation_history or []
                conversation_history.append(message)
                
                # Trim conversation if too long
                if len(conversation_history) > self.max_conversation_length:
                    conversation_history = conversation_history[-self.max_conversation_length:]
                
                session.conversation_history = conversation_history
                session.last_activity = datetime.utcnow()
                db.commit()
                
                # Update cache
                if self.redis_client:
                    await self._cache_session(session_token, session)
        
        # Also update Redis cache directly if available
        if self.redis_client:
            await self._add_message_to_cache(session_token, message)
    
    async def get_conversation_history(
        self,
        session_token: str,
        limit: Optional[int] = None,
        db: Session = None
    ) -> List[Dict]:
        """Get conversation history for a session"""
        
        session = await self.get_session(session_token, db)
        if not session:
            return []
        
        history = session.conversation_history or []
        
        if limit:
            return history[-limit:]
        
        return history
    
    async def update_learning_progress(
        self,
        session_token: str,
        progress_data: Dict,
        db: Session = None
    ) -> None:
        """Update learning progress for the session"""
        
        if db:
            session = await self.get_session(session_token, db)
            if session:
                current_progress = session.learning_progress or {}
                current_progress.update(progress_data)
                session.learning_progress = current_progress
                session.last_activity = datetime.utcnow()
                db.commit()
                
                if self.redis_client:
                    await self._cache_session(session_token, session)
    
    async def update_story_context(
        self,
        session_token: str,
        story_context: Dict,
        db: Session = None
    ) -> None:
        """Update current story context"""
        
        if db:
            session = await self.get_session(session_token, db)
            if session:
                session.current_story_context = story_context
                session.last_activity = datetime.utcnow()
                db.commit()
                
                if self.redis_client:
                    await self._cache_session(session_token, session)
    
    async def analyze_personality_adaptations(
        self,
        session_token: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """Analyze user interactions to adapt personality and preferences"""
        
        session = await self.get_session(session_token, db)
        if not session:
            return {}
        
        conversation_history = session.conversation_history or []
        
        if len(conversation_history) < self.personality_analysis_threshold:
            return session.personality_adaptations or {}
        
        # Analyze recent user messages
        user_messages = [
            msg for msg in conversation_history[-20:]  # Last 20 messages
            if msg.get("role") == "user"
        ]
        
        if not user_messages:
            return session.personality_adaptations or {}
        
        # Analyze patterns
        adaptations = await self._analyze_interaction_patterns(user_messages)
        
        # Update adaptations in session
        if db and adaptations:
            current_adaptations = session.personality_adaptations or {}
            current_adaptations.update(adaptations)
            session.personality_adaptations = current_adaptations
            db.commit()
            
            if self.redis_client:
                await self._cache_session(session_token, session)
        
        return adaptations
    
    async def _analyze_interaction_patterns(self, user_messages: List[Dict]) -> Dict[str, Any]:
        """Analyze user interaction patterns to determine adaptations"""
        
        adaptations = {}
        
        if not user_messages:
            return adaptations
        
        # Analyze message characteristics
        total_messages = len(user_messages)
        total_length = sum(len(msg.get("content", "")) for msg in user_messages)
        avg_message_length = total_length / total_messages if total_messages > 0 else 0
        
        # Determine communication style
        if avg_message_length > 200:
            adaptations["communication_preference"] = "detailed"
        elif avg_message_length < 50:
            adaptations["communication_preference"] = "concise"
        else:
            adaptations["communication_preference"] = "balanced"
        
        # Analyze question asking frequency
        question_count = sum(
            1 for msg in user_messages
            if "?" in msg.get("content", "")
        )
        question_ratio = question_count / total_messages if total_messages > 0 else 0
        
        if question_ratio > 0.3:
            adaptations["engagement_style"] = "inquisitive"
        elif question_ratio < 0.1:
            adaptations["engagement_style"] = "declarative"
        else:
            adaptations["engagement_style"] = "balanced"
        
        # Analyze emotional indicators
        positive_words = ["great", "awesome", "love", "excellent", "amazing", "fantastic"]
        negative_words = ["difficult", "hard", "confused", "stuck", "frustrated", "challenging"]
        
        positive_count = sum(
            sum(1 for word in positive_words if word in msg.get("content", "").lower())
            for msg in user_messages
        )
        negative_count = sum(
            sum(1 for word in negative_words if word in msg.get("content", "").lower())
            for msg in user_messages
        )
        
        if positive_count > negative_count * 2:
            adaptations["emotional_tone"] = "optimistic"
        elif negative_count > positive_count * 2:
            adaptations["emotional_tone"] = "needs_support"
        else:
            adaptations["emotional_tone"] = "neutral"
        
        # Analyze learning preference indicators
        visual_words = ["see", "show", "picture", "diagram", "visual", "image"]
        analytical_words = ["analyze", "break down", "step by step", "detailed", "systematic"]
        practical_words = ["example", "practice", "try", "hands-on", "apply", "use"]
        
        visual_score = sum(
            sum(1 for word in visual_words if word in msg.get("content", "").lower())
            for msg in user_messages
        )
        analytical_score = sum(
            sum(1 for word in analytical_words if word in msg.get("content", "").lower())
            for msg in user_messages
        )
        practical_score = sum(
            sum(1 for word in practical_words if word in msg.get("content", "").lower())
            for msg in user_messages
        )
        
        max_score = max(visual_score, analytical_score, practical_score)
        if max_score > 0:
            if visual_score == max_score:
                adaptations["inferred_learning_style"] = "visual"
            elif analytical_score == max_score:
                adaptations["inferred_learning_style"] = "analytical"
            else:
                adaptations["inferred_learning_style"] = "practical"
        
        # Determine pacing preference
        time_indicators = [msg.get("metadata", {}).get("response_time") for msg in user_messages]
        valid_times = [t for t in time_indicators if t is not None]
        
        if valid_times:
            avg_response_time = sum(valid_times) / len(valid_times)
            if avg_response_time < 5:  # Quick responses
                adaptations["pacing_preference"] = "fast"
            elif avg_response_time > 30:  # Slow responses
                adaptations["pacing_preference"] = "thoughtful"
            else:
                adaptations["pacing_preference"] = "moderate"
        
        adaptations["analysis_timestamp"] = datetime.utcnow().isoformat()
        adaptations["message_count_analyzed"] = total_messages
        
        return adaptations
    
    async def get_personalized_recommendations(
        self,
        session_token: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get personalized recommendations based on memory and adaptations"""
        
        session = await self.get_session(session_token, db)
        if not session:
            return {}
        
        adaptations = session.personality_adaptations or {}
        learning_progress = session.learning_progress or {}
        conversation_history = session.conversation_history or []
        
        recommendations = {
            "story_preferences": self._recommend_story_preferences(adaptations),
            "interaction_style": self._recommend_interaction_style(adaptations),
            "content_delivery": self._recommend_content_delivery(adaptations, learning_progress),
            "engagement_strategies": self._recommend_engagement_strategies(adaptations, conversation_history)
        }
        
        return recommendations
    
    def _recommend_story_preferences(self, adaptations: Dict) -> Dict[str, Any]:
        """Recommend story preferences based on adaptations"""
        
        preferences = {
            "pace": "moderate",
            "detail_level": "balanced",
            "interaction_frequency": "moderate"
        }
        
        # Adjust based on communication preference
        comm_pref = adaptations.get("communication_preference", "balanced")
        if comm_pref == "detailed":
            preferences["detail_level"] = "high"
            preferences["interaction_frequency"] = "high"
        elif comm_pref == "concise":
            preferences["detail_level"] = "low"
            preferences["pace"] = "fast"
        
        # Adjust based on engagement style
        engagement = adaptations.get("engagement_style", "balanced")
        if engagement == "inquisitive":
            preferences["interaction_frequency"] = "high"
        elif engagement == "declarative":
            preferences["interaction_frequency"] = "low"
        
        # Adjust based on pacing preference
        pacing = adaptations.get("pacing_preference", "moderate")
        if pacing == "fast":
            preferences["pace"] = "fast"
        elif pacing == "thoughtful":
            preferences["pace"] = "slow"
            preferences["detail_level"] = "high"
        
        return preferences
    
    def _recommend_interaction_style(self, adaptations: Dict) -> Dict[str, Any]:
        """Recommend interaction style adjustments"""
        
        style = {
            "tone": "encouraging",
            "explanation_depth": "moderate",
            "question_frequency": "balanced"
        }
        
        emotional_tone = adaptations.get("emotional_tone", "neutral")
        if emotional_tone == "needs_support":
            style["tone"] = "supportive"
            style["explanation_depth"] = "detailed"
        elif emotional_tone == "optimistic":
            style["tone"] = "enthusiastic"
            style["question_frequency"] = "high"
        
        learning_style = adaptations.get("inferred_learning_style")
        if learning_style == "visual":
            style["visual_elements"] = "high"
        elif learning_style == "analytical":
            style["explanation_depth"] = "detailed"
            style["logical_structure"] = "high"
        elif learning_style == "practical":
            style["examples"] = "high"
            style["hands_on_activities"] = "high"
        
        return style
    
    def _recommend_content_delivery(self, adaptations: Dict, learning_progress: Dict) -> Dict[str, Any]:
        """Recommend content delivery adjustments"""
        
        delivery = {
            "chunk_size": "medium",
            "repetition_frequency": "moderate",
            "complexity_progression": "gradual"
        }
        
        # Adjust based on progress patterns
        if learning_progress.get("struggles_identified"):
            delivery["chunk_size"] = "small"
            delivery["repetition_frequency"] = "high"
        
        if learning_progress.get("fast_learner_indicators"):
            delivery["chunk_size"] = "large"
            delivery["complexity_progression"] = "accelerated"
        
        # Adjust based on communication preference
        comm_pref = adaptations.get("communication_preference", "balanced")
        if comm_pref == "concise":
            delivery["chunk_size"] = "small"
        elif comm_pref == "detailed":
            delivery["chunk_size"] = "large"
        
        return delivery
    
    def _recommend_engagement_strategies(self, adaptations: Dict, conversation_history: List[Dict]) -> List[str]:
        """Recommend engagement strategies"""
        
        strategies = []
        
        engagement_style = adaptations.get("engagement_style", "balanced")
        if engagement_style == "inquisitive":
            strategies.extend([
                "Include more interactive questions",
                "Provide opportunities for exploration",
                "Encourage hypothesis formation"
            ])
        elif engagement_style == "declarative":
            strategies.extend([
                "Provide clear, definitive explanations",
                "Use more direct instruction",
                "Include summary statements"
            ])
        
        emotional_tone = adaptations.get("emotional_tone", "neutral")
        if emotional_tone == "needs_support":
            strategies.extend([
                "Provide more encouragement",
                "Break down complex concepts further",
                "Celebrate small wins"
            ])
        elif emotional_tone == "optimistic":
            strategies.extend([
                "Introduce more challenges",
                "Provide advanced extensions",
                "Encourage peer collaboration"
            ])
        
        # Analyze recent engagement
        if len(conversation_history) > 10:
            recent_messages = conversation_history[-10:]
            if all(len(msg.get("content", "")) < 50 for msg in recent_messages if msg.get("role") == "user"):
                strategies.append("Try more engaging, open-ended questions")
        
        return strategies
    
    def _generate_session_token(self) -> str:
        """Generate a unique session token"""
        import uuid
        return str(uuid.uuid4())
    
    async def _cache_session(self, session_token: str, session: UserSession) -> None:
        """Cache session in Redis"""
        if not self.redis_client:
            return
        
        try:
            session_data = {
                "user_id": session.user_id,
                "conversation_history": json.dumps(session.conversation_history or []),
                "current_story_context": json.dumps(session.current_story_context or {}),
                "learning_progress": json.dumps(session.learning_progress or {}),
                "personality_adaptations": json.dumps(session.personality_adaptations or {}),
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "expires_at": session.expires_at.isoformat()
            }
            
            cache_key = f"session:{session_token}"
            self.redis_client.hmset(cache_key, session_data)
            self.redis_client.expire(cache_key, 86400)  # 24 hours
            
        except Exception as e:
            logger.warning(f"Failed to cache session: {e}")
    
    async def _get_cached_session(self, session_token: str) -> Optional[UserSession]:
        """Get session from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = f"session:{session_token}"
            session_data = self.redis_client.hgetall(cache_key)
            
            if not session_data:
                return None
            
            # Check if expired
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if expires_at <= datetime.utcnow():
                self.redis_client.delete(cache_key)
                return None
            
            # Create UserSession object
            session = UserSession(
                user_id=int(session_data["user_id"]),
                session_token=session_token,
                conversation_history=json.loads(session_data.get("conversation_history", "[]")),
                current_story_context=json.loads(session_data.get("current_story_context", "{}")),
                learning_progress=json.loads(session_data.get("learning_progress", "{}")),
                personality_adaptations=json.loads(session_data.get("personality_adaptations", "{}")),
                expires_at=expires_at
            )
            
            if session_data.get("last_activity"):
                session.last_activity = datetime.fromisoformat(session_data["last_activity"])
            
            return session
            
        except Exception as e:
            logger.warning(f"Failed to get cached session: {e}")
            return None
    
    async def _add_message_to_cache(self, session_token: str, message: Dict) -> None:
        """Add message to cached conversation history"""
        if not self.redis_client:
            return
        
        try:
            cache_key = f"session:{session_token}"
            
            # Get current history
            current_history_json = self.redis_client.hget(cache_key, "conversation_history")
            if current_history_json:
                current_history = json.loads(current_history_json)
            else:
                current_history = []
            
            # Add new message
            current_history.append(message)
            
            # Trim if too long
            if len(current_history) > self.max_conversation_length:
                current_history = current_history[-self.max_conversation_length:]
            
            # Update cache
            self.redis_client.hset(cache_key, "conversation_history", json.dumps(current_history))
            
        except Exception as e:
            logger.warning(f"Failed to add message to cache: {e}")


memory_service = ConversationalMemoryService()