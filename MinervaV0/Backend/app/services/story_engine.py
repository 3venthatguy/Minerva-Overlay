import json
import random
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.user import User, UserSession
from app.models.document import Document
from app.models.story import StoryTemplate, GeneratedStory
import logging

logger = logging.getLogger(__name__)


class StoryEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.narrative_frameworks = self._load_narrative_frameworks()
        self.character_archetypes = self._load_character_archetypes()
        self.story_genres = self._load_story_genres()
    
    def _load_narrative_frameworks(self) -> Dict[str, Dict]:
        """Load predefined narrative frameworks"""
        return {
            "hero_journey": {
                "name": "Hero's Journey",
                "description": "Classic monomyth structure where the user becomes a hero",
                "phases": [
                    "ordinary_world",
                    "call_to_adventure", 
                    "meeting_mentor",
                    "crossing_threshold",
                    "tests_and_trials",
                    "revelation",
                    "transformation",
                    "return_with_knowledge"
                ],
                "adaptability": "high"
            },
            "mystery_investigation": {
                "name": "Mystery Investigation",
                "description": "User becomes a detective solving learning-related mysteries",
                "phases": [
                    "discovery_of_mystery",
                    "gathering_clues",
                    "first_breakthrough",
                    "complications",
                    "final_investigation",
                    "revelation",
                    "resolution"
                ],
                "adaptability": "high"
            },
            "scientific_exploration": {
                "name": "Scientific Exploration",
                "description": "User as a researcher making discoveries",
                "phases": [
                    "observation",
                    "hypothesis_formation",
                    "experimentation",
                    "data_analysis",
                    "peer_review",
                    "breakthrough",
                    "publication"
                ],
                "adaptability": "medium"
            },
            "time_travel_adventure": {
                "name": "Time Travel Adventure",
                "description": "User travels through time to learn historical concepts",
                "phases": [
                    "departure",
                    "arrival_in_past",
                    "cultural_immersion",
                    "historical_challenge",
                    "key_insight",
                    "timeline_impact",
                    "return_home"
                ],
                "adaptability": "high"
            },
            "simulation_training": {
                "name": "Simulation Training",
                "description": "User in a virtual training environment",
                "phases": [
                    "briefing",
                    "basic_training",
                    "skill_building",
                    "scenario_practice",
                    "complex_challenges",
                    "mastery_test",
                    "graduation"
                ],
                "adaptability": "medium"
            }
        }
    
    def _load_character_archetypes(self) -> Dict[str, Dict]:
        """Load character archetypes for user personalization"""
        return {
            "explorer": {
                "name": "The Explorer",
                "traits": ["curious", "adventurous", "independent", "resourceful"],
                "motivation": "discovery and understanding",
                "approach": "hands-on experimentation"
            },
            "scholar": {
                "name": "The Scholar",
                "traits": ["analytical", "methodical", "patient", "detail-oriented"],
                "motivation": "deep understanding and mastery",
                "approach": "systematic study and research"
            },
            "innovator": {
                "name": "The Innovator", 
                "traits": ["creative", "visionary", "ambitious", "problem-solving"],
                "motivation": "creating something new",
                "approach": "experimental and iterative"
            },
            "helper": {
                "name": "The Helper",
                "traits": ["empathetic", "collaborative", "supportive", "communicative"],
                "motivation": "helping others and making impact",
                "approach": "learning through teaching and sharing"
            },
            "achiever": {
                "name": "The Achiever",
                "traits": ["goal-oriented", "competitive", "determined", "efficient"],
                "motivation": "success and recognition",
                "approach": "focused practice and optimization"
            }
        }
    
    def _load_story_genres(self) -> Dict[str, Dict]:
        """Load story genre templates"""
        return {
            "adventure": {
                "name": "Adventure",
                "tone": "exciting, dynamic, challenging",
                "settings": ["unexplored territories", "dangerous missions", "epic quests"],
                "conflicts": ["overcoming obstacles", "facing fears", "time pressure"]
            },
            "mystery": {
                "name": "Mystery",
                "tone": "intriguing, suspenseful, analytical",
                "settings": ["research labs", "historical archives", "crime scenes"],
                "conflicts": ["solving puzzles", "uncovering secrets", "finding truth"]
            },
            "sci_fi": {
                "name": "Science Fiction",
                "tone": "futuristic, technological, innovative",
                "settings": ["space stations", "virtual reality", "advanced labs"],
                "conflicts": ["technological challenges", "ethical dilemmas", "future consequences"]
            },
            "historical": {
                "name": "Historical",
                "tone": "immersive, authentic, educational",
                "settings": ["historical periods", "ancient civilizations", "cultural events"],
                "conflicts": ["cultural challenges", "historical problems", "period accuracy"]
            },
            "fantasy": {
                "name": "Fantasy",
                "tone": "magical, wonder-filled, epic",
                "settings": ["magical realms", "enchanted libraries", "mystical academies"],
                "conflicts": ["magical challenges", "ancient knowledge", "mystical quests"]
            }
        }
    
    async def generate_personalized_story(
        self,
        document: Document,
        user: User,
        user_session: UserSession,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate a personalized story based on document content and user profile"""
        
        # Analyze user preferences and adapt story accordingly
        story_config = await self._analyze_user_preferences(user, user_session, preferences)
        
        # Select appropriate narrative framework
        framework = self._select_narrative_framework(document, story_config)
        
        # Create user character profile
        user_character = self._create_user_character(user, story_config)
        
        # Generate story content using AI
        story_content = await self._generate_story_content(
            document, framework, user_character, story_config
        )
        
        # Create interactive elements
        interactive_elements = self._create_interactive_elements(
            story_content, document, framework
        )
        
        return {
            "story_content": story_content,
            "framework": framework,
            "user_character": user_character,
            "interactive_elements": interactive_elements,
            "personalization_factors": story_config
        }
    
    async def _analyze_user_preferences(
        self,
        user: User,
        user_session: UserSession,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze user preferences to customize story generation"""
        
        config = {
            "learning_style": user.learning_style or "visual",
            "skill_level": user.skill_level or "beginner",
            "personality_traits": user.personality_traits or {},
            "interests": user.interests or [],
            "preferred_genres": user.preferred_story_genres or ["adventure"],
            "session_context": user_session.conversation_history or [],
            "previous_adaptations": user_session.personality_adaptations or {}
        }
        
        # Override with any explicit preferences
        if preferences:
            config.update(preferences)
        
        # Analyze conversation history for personality insights
        if user_session.conversation_history:
            personality_insights = await self._analyze_conversation_personality(
                user_session.conversation_history
            )
            config["personality_traits"].update(personality_insights)
        
        return config
    
    async def _analyze_conversation_personality(self, conversation_history: List[Dict]) -> Dict:
        """Analyze user's personality from conversation history using AI"""
        
        if not conversation_history:
            return {}
        
        # Extract recent user messages
        user_messages = [
            msg["content"] for msg in conversation_history[-10:]
            if msg.get("role") == "user"
        ]
        
        if not user_messages:
            return {}
        
        try:
            prompt = f"""
            Analyze the following user messages and extract personality traits that would be useful for educational story adaptation. Focus on learning preferences, communication style, and engagement patterns.
            
            User messages:
            {json.dumps(user_messages, indent=2)}
            
            Return a JSON object with personality insights that include:
            - communication_style (formal/casual/technical/conversational)
            - engagement_level (high/medium/low)
            - question_asking_tendency (frequent/occasional/rare)
            - detail_preference (high/medium/low)
            - challenge_seeking (high/medium/low)
            
            Only include traits you can confidently identify. Return empty object if insufficient data.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.warning(f"Error analyzing conversation personality: {e}")
            return {}
    
    def _select_narrative_framework(self, document: Document, story_config: Dict) -> Dict:
        """Select the most appropriate narrative framework"""
        
        # Get document characteristics
        content_type = self._classify_content_type(document)
        difficulty_level = document.difficulty_level or "medium"
        
        # Consider user preferences
        preferred_genres = story_config.get("preferred_genres", ["adventure"])
        learning_style = story_config.get("learning_style", "visual")
        
        # Framework selection logic
        if content_type == "scientific" and "sci_fi" in preferred_genres:
            framework_key = "scientific_exploration"
        elif content_type == "historical" and "historical" in preferred_genres:
            framework_key = "time_travel_adventure"
        elif "mystery" in preferred_genres and learning_style in ["analytical", "reading"]:
            framework_key = "mystery_investigation"
        elif difficulty_level == "beginner":
            framework_key = "simulation_training"
        else:
            framework_key = "hero_journey"  # Default safe choice
        
        framework = self.narrative_frameworks[framework_key].copy()
        framework["selected_reason"] = f"Matched {content_type} content with {preferred_genres} preference"
        
        return framework
    
    def _classify_content_type(self, document: Document) -> str:
        """Classify document content type for framework selection"""
        
        content = (document.processed_content or "").lower()
        key_concepts = [c.lower() for c in (document.key_concepts or [])]
        
        # Classification rules
        if any(word in content for word in ["history", "historical", "century", "ancient", "civilization"]):
            return "historical"
        elif any(word in content for word in ["science", "research", "experiment", "hypothesis", "data"]):
            return "scientific"
        elif any(word in content for word in ["technical", "programming", "code", "algorithm", "software"]):
            return "technical"
        elif any(word in content for word in ["business", "management", "strategy", "marketing", "finance"]):
            return "business"
        else:
            return "general"
    
    def _create_user_character(self, user: User, story_config: Dict) -> Dict:
        """Create a character profile for the user within the story"""
        
        # Determine character archetype
        personality_traits = story_config.get("personality_traits", {})
        interests = story_config.get("interests", [])
        
        # Select archetype based on traits and preferences
        archetype_key = self._select_character_archetype(personality_traits, interests)
        archetype = self.character_archetypes[archetype_key].copy()
        
        # Customize character
        character = {
            "name": user.full_name or user.username,
            "archetype": archetype,
            "background": self._generate_character_background(user, story_config),
            "skills": self._determine_character_skills(user, story_config),
            "motivation": self._personalize_motivation(archetype["motivation"], interests),
            "growth_areas": story_config.get("learning_objectives", [])
        }
        
        return character
    
    def _select_character_archetype(self, personality_traits: Dict, interests: List) -> str:
        """Select character archetype based on user characteristics"""
        
        # Simple scoring system for archetype selection
        scores = {archetype: 0 for archetype in self.character_archetypes.keys()}
        
        # Score based on personality traits
        trait_mappings = {
            "curious": {"explorer": 3, "scholar": 2},
            "analytical": {"scholar": 3, "innovator": 2},
            "creative": {"innovator": 3, "explorer": 2},
            "helpful": {"helper": 3},
            "goal_oriented": {"achiever": 3},
            "detail_preference": {"scholar": 2, "achiever": 1},
            "challenge_seeking": {"explorer": 2, "achiever": 2, "innovator": 1}
        }
        
        for trait, trait_value in personality_traits.items():
            if trait in trait_mappings:
                for archetype, points in trait_mappings[trait].items():
                    scores[archetype] += points
        
        # Score based on interests
        interest_mappings = {
            "science": {"scholar": 2, "innovator": 1},
            "technology": {"innovator": 2, "explorer": 1},
            "research": {"scholar": 3},
            "teaching": {"helper": 3},
            "adventure": {"explorer": 2},
            "competition": {"achiever": 2}
        }
        
        for interest in interests:
            interest_lower = interest.lower()
            for keyword, archetype_scores in interest_mappings.items():
                if keyword in interest_lower:
                    for archetype, points in archetype_scores.items():
                        scores[archetype] += points
        
        # Select highest scoring archetype, with random fallback
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return random.choice(list(self.character_archetypes.keys()))
    
    def _generate_character_background(self, user: User, story_config: Dict) -> str:
        """Generate appropriate background story for the user character"""
        
        skill_level = story_config.get("skill_level", "beginner")
        interests = story_config.get("interests", [])
        
        backgrounds = {
            "beginner": [
                "a curious newcomer eager to learn",
                "someone taking their first steps into this field",
                "a determined beginner ready for challenges"
            ],
            "intermediate": [
                "an experienced practitioner seeking deeper knowledge",
                "someone with solid foundations looking to expand",
                "a skilled individual ready for advanced challenges"
            ],
            "advanced": [
                "an expert exploring cutting-edge concepts",
                "a master seeking to push boundaries",
                "a seasoned professional diving into specialized areas"
            ]
        }
        
        base_background = random.choice(backgrounds.get(skill_level, backgrounds["beginner"]))
        
        if interests:
            interest_context = f" with particular interest in {', '.join(interests[:2])}"
            return base_background + interest_context
        
        return base_background
    
    def _determine_character_skills(self, user: User, story_config: Dict) -> List[str]:
        """Determine character's starting skills based on user profile"""
        
        skills = []
        
        # Base skills from learning style
        learning_style = story_config.get("learning_style", "visual")
        style_skills = {
            "visual": ["observation", "pattern recognition"],
            "auditory": ["listening", "verbal communication"],
            "kinesthetic": ["hands-on problem solving", "experimentation"],
            "reading": ["research", "analytical thinking"]
        }
        skills.extend(style_skills.get(learning_style, []))
        
        # Skills from interests
        interests = story_config.get("interests", [])
        for interest in interests[:3]:  # Limit to top 3 interests
            skills.append(f"{interest.lower()} knowledge")
        
        # Skills from personality traits
        personality_traits = story_config.get("personality_traits", {})
        if personality_traits.get("analytical"):
            skills.append("critical thinking")
        if personality_traits.get("creative"):
            skills.append("creative problem solving")
        
        return skills[:5]  # Limit to 5 skills
    
    def _personalize_motivation(self, base_motivation: str, interests: List[str]) -> str:
        """Personalize character motivation based on user interests"""
        
        if not interests:
            return base_motivation
        
        primary_interest = interests[0] if interests else "learning"
        return f"{base_motivation}, particularly in the field of {primary_interest.lower()}"
    
    async def _generate_story_content(
        self,
        document: Document,
        framework: Dict,
        user_character: Dict,
        story_config: Dict
    ) -> Dict[str, Any]:
        """Generate the actual story content using AI"""
        
        # Prepare context for AI generation
        context = self._prepare_story_context(document, framework, user_character, story_config)
        
        # Generate story structure
        story_structure = await self._generate_story_structure(context)
        
        # Generate detailed content for each phase
        story_phases = await self._generate_story_phases(story_structure, context)
        
        # Generate overall narrative
        full_narrative = await self._generate_full_narrative(story_phases, context)
        
        return {
            "structure": story_structure,
            "phases": story_phases,
            "full_narrative": full_narrative,
            "title": story_structure.get("title", "Your Learning Adventure"),
            "synopsis": story_structure.get("synopsis", "")
        }
    
    def _prepare_story_context(
        self,
        document: Document,
        framework: Dict,
        user_character: Dict,
        story_config: Dict
    ) -> Dict[str, Any]:
        """Prepare context for AI story generation"""
        
        return {
            "document": {
                "title": document.original_filename,
                "content_summary": (document.processed_content or "")[:2000],  # Limit content
                "key_concepts": document.key_concepts or [],
                "learning_objectives": document.learning_objectives or [],
                "difficulty_level": document.difficulty_level,
                "estimated_reading_time": document.estimated_reading_time
            },
            "framework": framework,
            "user_character": user_character,
            "story_config": {
                "preferred_genres": story_config.get("preferred_genres", []),
                "learning_style": story_config.get("learning_style"),
                "skill_level": story_config.get("skill_level"),
                "tone_preference": story_config.get("tone_preference", "engaging")
            }
        }
    
    async def _generate_story_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level story structure"""
        
        prompt = f"""
        Create a story structure for an educational narrative that transforms learning content into an engaging story where the user is the main character.
        
        Context:
        - Document: {context['document']['title']} 
        - Key concepts to teach: {', '.join(context['document']['key_concepts'][:10])}
        - Learning objectives: {', '.join(context['document']['learning_objectives'][:5])}
        - Narrative framework: {context['framework']['name']}
        - Framework phases: {', '.join(context['framework']['phases'])}
        - User character: {context['user_character']['name']} - {context['user_character']['archetype']['name']}
        - Character motivation: {context['user_character']['motivation']}
        - Preferred genres: {', '.join(context['story_config']['preferred_genres'])}
        - Learning style: {context['story_config']['learning_style']}
        - Skill level: {context['story_config']['skill_level']}
        
        Generate a JSON response with:
        {{
            "title": "Engaging story title",
            "synopsis": "Brief story overview (2-3 sentences)",
            "setting": "Where the story takes place",
            "central_conflict": "Main challenge the user must overcome",
            "learning_arc": "How the user grows and learns through the story",
            "phases": [
                {{
                    "phase_name": "name from framework",
                    "learning_objective": "what the user learns in this phase",
                    "story_objective": "what happens narratively",
                    "key_concepts": ["concepts taught in this phase"]
                }}
            ]
        }}
        
        Make the story personally engaging for the user character while ensuring all key concepts are naturally integrated into the narrative.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error generating story structure: {e}")
            # Return fallback structure
            return self._generate_fallback_structure(context)
    
    def _generate_fallback_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simple fallback story structure"""
        
        framework = context['framework']
        document = context['document']
        user_character = context['user_character']
        
        return {
            "title": f"{user_character['name']}'s Learning Quest",
            "synopsis": f"Follow {user_character['name']} as they embark on a journey to master {document['title']}.",
            "setting": "An interactive learning environment",
            "central_conflict": "Mastering new concepts and overcoming learning challenges",
            "learning_arc": "Progressive skill building through narrative engagement",
            "phases": [
                {
                    "phase_name": phase,
                    "learning_objective": f"Learn concepts related to {phase}",
                    "story_objective": f"Navigate challenges in {phase}",
                    "key_concepts": document['key_concepts'][:3] if document['key_concepts'] else []
                }
                for phase in framework['phases'][:5]  # Limit to 5 phases
            ]
        }
    
    async def _generate_story_phases(self, story_structure: Dict, context: Dict) -> List[Dict]:
        """Generate detailed content for each story phase"""
        
        phases = []
        
        for i, phase_info in enumerate(story_structure.get("phases", [])):
            phase_content = await self._generate_phase_content(phase_info, context, i)
            phases.append(phase_content)
        
        return phases
    
    async def _generate_phase_content(
        self,
        phase_info: Dict,
        context: Dict,
        phase_index: int
    ) -> Dict[str, Any]:
        """Generate content for a single story phase"""
        
        prompt = f"""
        Generate detailed content for phase {phase_index + 1} of an educational story.
        
        Phase Information:
        - Phase name: {phase_info['phase_name']}
        - Learning objective: {phase_info['learning_objective']}
        - Story objective: {phase_info['story_objective']}
        - Key concepts to teach: {', '.join(phase_info.get('key_concepts', []))}
        
        Story Context:
        - Overall title: {context['document']['title']}
        - User character: {context['user_character']['name']} ({context['user_character']['archetype']['name']})
        - Character background: {context['user_character']['background']}
        - Learning style: {context['story_config']['learning_style']}
        
        Generate a JSON response with:
        {{
            "phase_title": "Title for this phase",
            "narrative": "Detailed story content (300-500 words) that naturally teaches the concepts",
            "key_moments": ["List of 3-5 important story moments"],
            "learning_checkpoints": [
                {{
                    "concept": "concept being taught",
                    "explanation": "how it's explained in the story",
                    "application": "how the user applies it"
                }}
            ],
            "challenges": ["Learning challenges the user faces"],
            "outcomes": ["What the user achieves/learns"]
        }}
        
        Make the narrative engaging and ensure concepts are taught through story action, not exposition.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            phase_content = json.loads(response.choices[0].message.content)
            phase_content["phase_info"] = phase_info
            return phase_content
            
        except Exception as e:
            logger.error(f"Error generating phase content: {e}")
            return self._generate_fallback_phase_content(phase_info, context, phase_index)
    
    def _generate_fallback_phase_content(
        self,
        phase_info: Dict,
        context: Dict,
        phase_index: int
    ) -> Dict[str, Any]:
        """Generate fallback content for a story phase"""
        
        return {
            "phase_title": f"Phase {phase_index + 1}: {phase_info['phase_name'].replace('_', ' ').title()}",
            "narrative": f"In this phase, {context['user_character']['name']} faces new challenges and learns important concepts about {', '.join(phase_info.get('key_concepts', ['the subject']))}.",
            "key_moments": [
                "Character encounters new information",
                "Character applies learning to overcome challenge", 
                "Character gains deeper understanding"
            ],
            "learning_checkpoints": [
                {
                    "concept": concept,
                    "explanation": f"Learn about {concept} through story events",
                    "application": f"Apply {concept} to solve problems"
                }
                for concept in phase_info.get('key_concepts', [])[:3]
            ],
            "challenges": [phase_info['learning_objective']],
            "outcomes": [f"Mastery of {phase_info['phase_name']}"],
            "phase_info": phase_info
        }
    
    async def _generate_full_narrative(self, story_phases: List[Dict], context: Dict) -> str:
        """Generate cohesive full narrative from story phases"""
        
        # For now, concatenate phase narratives with transitions
        full_story = ""
        
        for i, phase in enumerate(story_phases):
            if i > 0:
                full_story += "\n\n---\n\n"
            
            full_story += f"## {phase['phase_title']}\n\n"
            full_story += phase['narrative']
        
        return full_story
    
    def _create_interactive_elements(
        self,
        story_content: Dict,
        document: Document,
        framework: Dict
    ) -> Dict[str, Any]:
        """Create interactive elements for the story"""
        
        return {
            "decision_points": self._create_decision_points(story_content),
            "knowledge_checks": self._create_knowledge_checks(document, story_content),
            "progress_milestones": self._create_progress_milestones(framework, story_content),
            "engagement_activities": self._create_engagement_activities(story_content)
        }
    
    def _create_decision_points(self, story_content: Dict) -> List[Dict]:
        """Create decision points where users can choose their path"""
        
        decision_points = []
        phases = story_content.get("phases", [])
        
        for i, phase in enumerate(phases):
            if i < len(phases) - 1:  # Don't create decision point for last phase
                decision_points.append({
                    "phase_index": i,
                    "decision_prompt": f"How do you want to approach the challenge in {phase['phase_title']}?",
                    "options": [
                        {"text": "Take a methodical, step-by-step approach", "outcome": "detailed_analysis"},
                        {"text": "Trust your instincts and act quickly", "outcome": "intuitive_action"},
                        {"text": "Seek help and collaborate with others", "outcome": "collaborative_approach"}
                    ],
                    "impact": "Affects how the next phase unfolds and what additional insights you gain"
                })
        
        return decision_points
    
    def _create_knowledge_checks(self, document: Document, story_content: Dict) -> List[Dict]:
        """Create knowledge check questions integrated into the story"""
        
        knowledge_checks = []
        key_concepts = document.key_concepts or []
        
        for i, concept in enumerate(key_concepts[:5]):  # Limit to 5 checks
            knowledge_checks.append({
                "concept": concept,
                "question_type": "multiple_choice",
                "question": f"In the story, how does understanding {concept} help you progress?",
                "options": [
                    f"It allows you to solve the main challenge",
                    f"It helps you understand other characters' motivations",
                    f"It reveals important background information",
                    f"It opens up new possibilities for action"
                ],
                "correct_answer": 0,  # First option is generally correct
                "story_context": f"This knowledge check appears after learning about {concept} in the narrative",
                "feedback_success": f"Excellent! You've mastered how {concept} applies in this context.",
                "feedback_retry": f"Not quite. Think about how {concept} specifically helps in this situation."
            })
        
        return knowledge_checks
    
    def _create_progress_milestones(self, framework: Dict, story_content: Dict) -> List[Dict]:
        """Create progress tracking milestones"""
        
        phases = framework.get("phases", [])
        milestones = []
        
        for i, phase_name in enumerate(phases):
            milestone_percentage = ((i + 1) / len(phases)) * 100
            milestones.append({
                "phase_name": phase_name,
                "percentage": milestone_percentage,
                "title": f"Completed {phase_name.replace('_', ' ').title()}",
                "description": f"You've successfully navigated through the {phase_name.replace('_', ' ')} phase of your learning journey",
                "rewards": [
                    f"Unlocked insights about {phase_name}",
                    "Gained new skills and knowledge",
                    "Advanced your character development"
                ]
            })
        
        return milestones
    
    def _create_engagement_activities(self, story_content: Dict) -> List[Dict]:
        """Create additional engagement activities"""
        
        return [
            {
                "type": "reflection",
                "title": "Character Journal",
                "description": "Write a journal entry from your character's perspective about what you've learned",
                "prompt": "Reflect on your journey so far and the insights you've gained"
            },
            {
                "type": "creative_application",
                "title": "Apply Your Knowledge",
                "description": "Create a solution to a new problem using what you've learned",
                "prompt": "How would you use your new knowledge in a different scenario?"
            },
            {
                "type": "peer_sharing",
                "title": "Share Your Story",
                "description": "Share your learning journey with others",
                "prompt": "What part of your story would you share with someone else learning this topic?"
            }
        ]


story_engine = StoryEngine()