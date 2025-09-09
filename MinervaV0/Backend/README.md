# Minerva Learning Engine Backend

A FastAPI-based backend for an AI-powered learning app that transforms uploaded documents into interactive story-based learning experiences.

## Features

- **Document Upload & Processing**: Support for PDF, DOCX, TXT, and MD files with automatic content extraction and analysis
- **AI Story Generation**: Transforms educational content into personalized narrative experiences using OpenAI GPT-4
- **Adaptive User Profiles**: Learns from user interactions to personalize story experiences
- **Conversational Memory**: Tracks learning progress and adapts to user personality
- **Interactive Storytelling**: Decision points, knowledge checks, and progress tracking
- **Multiple Narrative Frameworks**: Hero's Journey, Mystery Investigation, Scientific Exploration, and more

## Architecture

### Core Components

1. **Document Processing Pipeline**
   - File upload and validation
   - Content extraction (PDF, DOCX, TXT, MD)
   - Text analysis and concept extraction
   - Content chunking for processing

2. **AI Story Engine**
   - Narrative framework selection
   - Character archetype matching
   - Personalized story generation
   - Interactive element creation

3. **User Profile & Memory System**
   - Learning style adaptation
   - Personality trait analysis
   - Conversation history tracking
   - Progress monitoring

4. **Interactive Chat System**
   - Context-aware AI responses
   - Learning companion functionality
   - Story-specific conversations
   - Adaptive communication style

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- OpenAI API key

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd MinervaV0/Backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up the database:
```bash
# Create PostgreSQL database
createdb minerva_db

# Run migrations (when implemented)
alembic upgrade head
```

5. Start Redis:
```bash
redis-server
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
Currently using simple user_id parameter. JWT authentication to be implemented.

## Endpoints Overview

### Documents API (`/api/v1/documents`)

#### Upload Document
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (PDF, DOCX, TXT, MD)
- user_id: int (default: 1)
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "filename": "unique_filename.pdf",
  "original_filename": "my_document.pdf",
  "file_type": "pdf",
  "file_size": 1024000,
  "processing_status": "uploaded",
  "created_at": "2023-12-07T10:00:00Z"
}
```

#### List Documents
```http
GET /api/v1/documents?user_id=1&skip=0&limit=100
```

#### Get Document Details
```http
GET /api/v1/documents/{document_id}?user_id=1
```

#### Get Document Content
```http
GET /api/v1/documents/{document_id}/content?user_id=1
```

### Stories API (`/api/v1/stories`)

#### Generate Story
```http
POST /api/v1/stories/generate
Content-Type: application/json

{
  "document_id": 1,
  "user_id": 1,
  "session_token": "session_uuid",
  "preferences": {
    "genre": "adventure",
    "difficulty": "medium",
    "narrative_style": "first_person"
  }
}
```

#### Get Story Details
```http
GET /api/v1/stories/{story_id}?user_id=1
```

#### Get Story Phase
```http
GET /api/v1/stories/{story_id}/phases/{phase_index}?user_id=1
```

#### Make Story Decision
```http
POST /api/v1/stories/{story_id}/decisions
Content-Type: application/json

{
  "story_id": 1,
  "session_token": "session_uuid",
  "decision_point_id": "decision_1",
  "selected_option": 0,
  "user_reasoning": "I chose this because..."
}
```

#### Submit Knowledge Check
```http
POST /api/v1/stories/{story_id}/knowledge-check
Content-Type: application/json

{
  "story_id": 1,
  "session_token": "session_uuid",
  "question_id": "q1",
  "selected_answer": 2,
  "confidence_level": 8
}
```

### Users API (`/api/v1/users`)

#### Create User
```http
POST /api/v1/users
Content-Type: application/json

{
  "username": "learner123",
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "learning_style": "visual",
  "interests": ["science", "technology"],
  "skill_level": "intermediate",
  "preferred_story_genres": ["adventure", "sci_fi"]
}
```

#### Create Learning Session
```http
POST /api/v1/users/{user_id}/sessions
```

#### Get Session Details
```http
GET /api/v1/users/{user_id}/sessions/{session_token}
```

#### Update Personality Traits
```http
POST /api/v1/users/{user_id}/personality
Content-Type: application/json

{
  "traits": {
    "analytical": true,
    "creative": false,
    "collaborative": true
  },
  "source": "user_input"
}
```

### Chat API (`/api/v1/chat`)

#### Send Message
```http
POST /api/v1/chat/message
Content-Type: application/json

{
  "content": "How am I doing in my story?",
  "context_type": "story",
  "story_id": 1,
  "metadata": {
    "timestamp": "2023-12-07T10:00:00Z"
  }
}
```

**Response:**
```json
{
  "content": "You're doing great! You've completed 60% of your learning story...",
  "response_type": "encouragement",
  "suggestions": [
    "Continue with the next chapter",
    "Review what you've learned so far"
  ],
  "learning_insights": {
    "concepts_learned_count": 5,
    "story_completion": 60
  },
  "story_progression": {
    "current_phase": 3,
    "completion_percentage": 60,
    "next_milestone": "75% - Three Quarters Done"
  }
}
```

#### Get Chat Suggestions
```http
GET /api/v1/chat/suggestions/{session_token}?context_type=story
```

## Usage Examples

### Complete Learning Flow

1. **Create User Profile**
```python
import requests

# Create user
user_data = {
    "username": "alice_learner",
    "email": "alice@example.com",
    "password": "password123",
    "learning_style": "visual",
    "interests": ["artificial intelligence", "machine learning"],
    "skill_level": "beginner"
}

response = requests.post("http://localhost:8000/api/v1/users", json=user_data)
user = response.json()
user_id = user["id"]
```

2. **Create Learning Session**
```python
response = requests.post(f"http://localhost:8000/api/v1/users/{user_id}/sessions")
session_data = response.json()
session_token = session_data["session_token"]
```

3. **Upload Document**
```python
with open("ml_basics.pdf", "rb") as f:
    files = {"file": f}
    data = {"user_id": user_id}
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload", 
        files=files, 
        data=data
    )
    document = response.json()
    document_id = document["id"]
```

4. **Generate Personalized Story**
```python
story_request = {
    "document_id": document_id,
    "user_id": user_id,
    "session_token": session_token,
    "preferences": {
        "genre": "sci_fi",
        "narrative_style": "adventure"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/stories/generate", 
    json=story_request
)
story = response.json()
story_id = story["id"]
```

5. **Interactive Learning**
```python
# Chat about the story
chat_message = {
    "content": "I'm ready to start my learning adventure!",
    "context_type": "story",
    "story_id": story_id
}

response = requests.post(
    "http://localhost:8000/api/v1/chat/message",
    json=chat_message,
    params={"user_id": user_id, "session_token": session_token}
)
ai_response = response.json()
print(ai_response["content"])
```

6. **Progress Through Story**
```python
# Get first phase
response = requests.get(
    f"http://localhost:8000/api/v1/stories/{story_id}/phases/0",
    params={"user_id": user_id}
)
phase = response.json()

# Make a decision
if phase["decision_points"]:
    decision = {
        "story_id": story_id,
        "session_token": session_token,
        "decision_point_id": phase["decision_points"][0]["id"],
        "selected_option": 0
    }
    
    response = requests.post(
        f"http://localhost:8000/api/v1/stories/{story_id}/decisions",
        json=decision
    )
```

## Data Models

### User Profile
```python
{
  "id": int,
  "username": str,
  "email": str,
  "learning_style": "visual" | "auditory" | "kinesthetic" | "reading",
  "skill_level": "beginner" | "intermediate" | "advanced",
  "interests": List[str],
  "personality_traits": {
    "active_traits": Dict[str, Any],
    "update_history": List[Dict],
    "last_updated": str
  }
}
```

### Story Structure
```python
{
  "title": str,
  "synopsis": str,
  "setting": str,
  "central_conflict": str,
  "learning_arc": str,
  "phases": [
    {
      "phase_name": str,
      "phase_title": str,
      "narrative": str,
      "learning_objective": str,
      "key_concepts": List[str],
      "learning_checkpoints": List[Dict],
      "challenges": List[str]
    }
  ]
}
```

### Progress Tracking
```python
{
  "completion_percentage": float,
  "current_chapter": int,
  "concepts_learned": List[str],
  "decisions_made": List[Dict],
  "knowledge_check_results": List[Dict],
  "engagement_metrics": {
    "total_time_spent": int,
    "session_count": int,
    "average_session_length": float
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | Required |
| OPENAI_API_KEY | OpenAI API key for story generation | Required |
| REDIS_URL | Redis connection string | redis://localhost:6379 |
| SECRET_KEY | JWT secret key | Required |
| UPLOAD_DIR | Directory for file uploads | ./uploads |
| MAX_FILE_SIZE | Maximum file size in bytes | 10485760 (10MB) |

### Supported File Types

- **PDF**: Uses PyPDF2 for text extraction
- **DOCX**: Uses python-docx for text extraction  
- **TXT**: Plain text files with encoding detection
- **MD**: Markdown files

## Narrative Frameworks

The system includes several built-in narrative frameworks:

1. **Hero's Journey**: Classic monomyth structure
2. **Mystery Investigation**: Detective-style learning
3. **Scientific Exploration**: Research-based discovery
4. **Time Travel Adventure**: Historical learning contexts
5. **Simulation Training**: Skill-building environments

## Personality Adaptation

The system analyzes user interactions to adapt:

- **Communication Style**: Detailed vs. concise responses
- **Learning Pace**: Fast vs. thoughtful progression
- **Engagement Type**: Question-driven vs. declarative
- **Content Preference**: Visual vs. textual vs. interactive

## Development

### Project Structure
```
Backend/
├── app/
│   ├── api/          # API route handlers
│   ├── core/         # Core configuration
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── utils/        # Utility functions
├── uploads/          # File storage
├── requirements.txt  # Dependencies
└── .env.example     # Environment template
```

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions or issues:
- Create an issue in the repository
- Check the API documentation at `/docs` when running locally
- Review the example implementations above