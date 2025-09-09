"""
Minerva Learning Engine - Example Usage

This script demonstrates how to use the Minerva API to create 
a complete learning experience from document upload to interactive storytelling.
"""

import requests
import json
import time
from typing import Dict, Any

class MinervaClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user profile"""
        response = self.session.post(f"{self.base_url}/api/v1/users", json=user_data)
        response.raise_for_status()
        return response.json()
    
    def create_session(self, user_id: int) -> str:
        """Create a learning session and return session token"""
        response = self.session.post(f"{self.base_url}/api/v1/users/{user_id}/sessions")
        response.raise_for_status()
        return response.json()["session_token"]
    
    def upload_document(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """Upload a document for processing"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"user_id": user_id}
            response = self.session.post(
                f"{self.base_url}/api/v1/documents/upload",
                files=files,
                data=data
            )
        response.raise_for_status()
        return response.json()
    
    def wait_for_processing(self, document_id: int, user_id: int, timeout: int = 300) -> bool:
        """Wait for document processing to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.session.get(
                f"{self.base_url}/api/v1/documents/{document_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            doc = response.json()
            
            if doc["processing_status"] == "completed":
                return True
            elif doc["processing_status"] == "error":
                raise Exception(f"Document processing failed: {doc.get('processing_error')}")
            
            print(f"Processing status: {doc['processing_status']}...")
            time.sleep(5)
        
        raise TimeoutError("Document processing timeout")
    
    def generate_story(self, document_id: int, user_id: int, session_token: str, 
                      preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a personalized story from a document"""
        story_request = {
            "document_id": document_id,
            "user_id": user_id,
            "session_token": session_token,
            "preferences": preferences or {}
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/stories/generate",
            json=story_request
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_story_generation(self, story_id: int, user_id: int, timeout: int = 300) -> bool:
        """Wait for story generation to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.session.get(
                f"{self.base_url}/api/v1/stories/{story_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            story = response.json()
            
            if story["current_progress"]["status"] == "completed":
                return True
            elif story["current_progress"]["status"] == "error":
                raise Exception("Story generation failed")
            
            print(f"Story generation status: {story['current_progress']['status']}...")
            time.sleep(10)
        
        raise TimeoutError("Story generation timeout")
    
    def chat(self, message: str, user_id: int, session_token: str, 
             context_type: str = "general", story_id: int = None) -> Dict[str, Any]:
        """Send a chat message to the AI companion"""
        chat_data = {
            "content": message,
            "context_type": context_type,
            "story_id": story_id
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/chat/message",
            json=chat_data,
            params={"user_id": user_id, "session_token": session_token}
        )
        response.raise_for_status()
        return response.json()
    
    def get_story_phase(self, story_id: int, phase_index: int, user_id: int) -> Dict[str, Any]:
        """Get details for a specific story phase"""
        response = self.session.get(
            f"{self.base_url}/api/v1/stories/{story_id}/phases/{phase_index}",
            params={"user_id": user_id}
        )
        response.raise_for_status()
        return response.json()
    
    def make_decision(self, story_id: int, session_token: str, decision_point_id: str, 
                     selected_option: int, reasoning: str = None) -> Dict[str, Any]:
        """Make a decision in the story"""
        decision_data = {
            "story_id": story_id,
            "session_token": session_token,
            "decision_point_id": decision_point_id,
            "selected_option": selected_option,
            "user_reasoning": reasoning
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/stories/{story_id}/decisions",
            json=decision_data
        )
        response.raise_for_status()
        return response.json()
    
    def answer_knowledge_check(self, story_id: int, session_token: str, 
                              question_id: str, selected_answer: int,
                              confidence: int = None) -> Dict[str, Any]:
        """Answer a knowledge check question"""
        answer_data = {
            "story_id": story_id,
            "session_token": session_token,
            "question_id": question_id,
            "selected_answer": selected_answer,
            "confidence_level": confidence
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/stories/{story_id}/knowledge-check",
            json=answer_data
        )
        response.raise_for_status()
        return response.json()


def example_complete_learning_journey():
    """Complete example of a learning journey with Minerva"""
    
    client = MinervaClient()
    
    print("🌟 Starting Minerva Learning Journey Example")
    print("=" * 50)
    
    # Step 1: Create user profile
    print("\n1. Creating user profile...")
    user_data = {
        "username": "alice_explorer",
        "email": "alice@example.com", 
        "password": "learning123",
        "full_name": "Alice Explorer",
        "learning_style": "visual",
        "interests": ["artificial intelligence", "machine learning", "data science"],
        "skill_level": "beginner",
        "preferred_story_genres": ["adventure", "sci_fi", "mystery"]
    }
    
    try:
        user = client.create_user(user_data)
        user_id = user["id"]
        print(f"✅ User created successfully: {user['username']} (ID: {user_id})")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print("⚠️  User already exists, using default user_id=1")
            user_id = 1
        else:
            raise
    
    # Step 2: Create learning session
    print("\n2. Creating learning session...")
    session_token = client.create_session(user_id)
    print(f"✅ Session created: {session_token[:8]}...")
    
    # Step 3: Upload document
    print("\n3. Uploading document...")
    # For this example, we'll create a sample document
    sample_content = """
    Introduction to Machine Learning
    
    Machine learning is a subset of artificial intelligence (AI) that provides systems 
    the ability to automatically learn and improve from experience without being 
    explicitly programmed. Machine learning focuses on the development of computer 
    programs that can access data and use it to learn for themselves.
    
    Key Concepts:
    - Supervised Learning: Learning with labeled data
    - Unsupervised Learning: Finding patterns in unlabeled data  
    - Reinforcement Learning: Learning through reward and punishment
    - Neural Networks: Computing systems inspired by biological neural networks
    - Deep Learning: Neural networks with multiple layers
    
    Applications:
    Machine learning is used in various applications such as email filtering, 
    detection of network intruders, and computer vision.
    """
    
    # Create sample document
    with open("sample_ml_intro.txt", "w") as f:
        f.write(sample_content)
    
    try:
        document = client.upload_document("sample_ml_intro.txt", user_id)
        document_id = document["id"]
        print(f"✅ Document uploaded: {document['original_filename']} (ID: {document_id})")
        
        # Step 4: Wait for processing
        print("\n4. Processing document...")
        client.wait_for_processing(document_id, user_id)
        print("✅ Document processing completed")
        
    except Exception as e:
        print(f"❌ Error uploading document: {e}")
        return
    
    # Step 5: Generate personalized story
    print("\n5. Generating personalized story...")
    story_preferences = {
        "genre": "adventure",
        "narrative_style": "first_person",
        "difficulty": "beginner_friendly",
        "focus_areas": ["practical_examples", "visual_learning"]
    }
    
    story = client.generate_story(document_id, user_id, session_token, story_preferences)
    story_id = story["id"]
    print(f"✅ Story generation started: {story['title']}")
    
    # Wait for story generation
    print("   Waiting for AI to create your personalized story...")
    client.wait_for_story_generation(story_id, user_id)
    print("✅ Story generation completed!")
    
    # Step 6: Initial chat interaction
    print("\n6. Starting conversation with Minerva...")
    chat_response = client.chat(
        "Hi Minerva! I'm excited to start my machine learning adventure. What should I expect?",
        user_id, session_token, "story", story_id
    )
    print(f"🤖 Minerva: {chat_response['content']}")
    
    if chat_response.get('suggestions'):
        print("\n   💡 Suggestions:")
        for suggestion in chat_response['suggestions'][:3]:
            print(f"      • {suggestion}")
    
    # Step 7: Explore first story phase
    print("\n7. Exploring the first chapter...")
    phase_0 = client.get_story_phase(story_id, 0, user_id)
    print(f"📖 Chapter: {phase_0['phase_title']}")
    print(f"📝 Status: {phase_0['completion_status']}")
    
    if phase_0['narrative']:
        # Show first few sentences of narrative
        narrative_preview = '. '.join(phase_0['narrative'].split('. ')[:3]) + '...'
        print(f"📚 Story preview: {narrative_preview}")
    
    # Step 8: Make a decision if available
    if phase_0.get('decision_points'):
        print("\n8. Making a story decision...")
        decision_point = phase_0['decision_points'][0]
        print(f"🤔 Decision: {decision_point['decision_prompt']}")
        
        for i, option in enumerate(decision_point['options']):
            print(f"   {i + 1}. {option['text']}")
        
        # Make the first choice
        decision_result = client.make_decision(
            story_id, session_token, decision_point['id'], 0,
            "I choose the first option as it aligns with my learning style"
        )
        print(f"✅ Decision made: {decision_result['consequence']}")
    
    # Step 9: Continue conversation about learning
    print("\n9. Reflecting on learning progress...")
    reflection_response = client.chat(
        "How am I doing so far? What concepts should I focus on next?",
        user_id, session_token, "learning", story_id
    )
    print(f"🤖 Minerva: {reflection_response['content']}")
    
    # Step 10: Check progress
    print("\n10. Checking learning progress...")
    try:
        progress_response = client.session.get(
            f"{client.base_url}/api/v1/stories/{story_id}/progress",
            params={"user_id": user_id}
        )
        progress_response.raise_for_status()
        progress = progress_response.json()
        
        print(f"📊 Progress: {progress['completion_percentage']:.1f}% complete")
        print(f"🧠 Concepts learned: {len(progress['concepts_learned'])}")
        print(f"⚡ Decisions made: {len(progress['decisions_made'])}")
        
        if progress.get('achievements'):
            print("🏆 Achievements:")
            for achievement in progress['achievements']:
                print(f"   {achievement['icon']} {achievement['title']}: {achievement['description']}")
    
    except Exception as e:
        print(f"⚠️  Could not fetch progress: {e}")
    
    print("\n🎉 Learning journey example completed!")
    print("You can continue by:")
    print("   • Proceeding to the next story phase")
    print("   • Asking Minerva questions about the concepts")
    print("   • Making more decisions to shape your story")
    print("   • Uploading additional documents to learn about")
    
    # Cleanup
    import os
    if os.path.exists("sample_ml_intro.txt"):
        os.remove("sample_ml_intro.txt")


def example_document_analysis():
    """Example of analyzing document content"""
    
    client = MinervaClient()
    
    print("\n📄 Document Analysis Example")
    print("=" * 30)
    
    # Create a more complex sample document
    complex_content = """
    Advanced Neural Networks and Deep Learning
    
    Chapter 1: Introduction to Neural Networks
    
    Neural networks are computing systems vaguely inspired by the biological neural 
    networks that constitute animal brains. The neural network itself is not an 
    algorithm, but rather a framework for many different machine learning algorithms 
    to work together and process complex data inputs.
    
    1.1 Basic Structure
    - Input Layer: Receives the initial data
    - Hidden Layers: Process the data through weighted connections
    - Output Layer: Produces the final result
    - Activation Functions: Determine neuron output (ReLU, Sigmoid, Tanh)
    
    1.2 Learning Process
    Neural networks learn through backpropagation, which involves:
    1. Forward pass: Data flows from input to output
    2. Loss calculation: Compare output with expected result
    3. Backward pass: Adjust weights to minimize loss
    4. Iteration: Repeat until convergence
    
    Chapter 2: Deep Learning Architectures
    
    2.1 Convolutional Neural Networks (CNNs)
    Used primarily for image processing and computer vision tasks.
    Key components include convolution layers, pooling layers, and fully connected layers.
    
    2.2 Recurrent Neural Networks (RNNs)
    Designed for sequential data like text or time series.
    Variants include LSTM (Long Short-Term Memory) and GRU (Gated Recurrent Unit).
    
    2.3 Transformer Architecture
    Revolutionary architecture that uses attention mechanisms.
    Forms the basis for models like BERT, GPT, and other large language models.
    """
    
    with open("complex_neural_networks.txt", "w") as f:
        f.write(complex_content)
    
    try:
        # Upload document
        print("Uploading complex document...")
        document = client.upload_document("complex_neural_networks.txt", 1)
        document_id = document["id"]
        
        # Wait for processing
        print("Processing document content...")
        client.wait_for_processing(document_id, 1)
        
        # Get processed content
        response = client.session.get(
            f"{client.base_url}/api/v1/documents/{document_id}/content",
            params={"user_id": 1}
        )
        response.raise_for_status()
        content_data = response.json()
        
        doc_info = content_data["document"]
        print(f"\n📊 Document Analysis Results:")
        print(f"   • File: {doc_info['original_filename']}")
        print(f"   • Type: {doc_info['file_type']}")
        print(f"   • Size: {doc_info['file_size']} bytes")
        print(f"   • Difficulty: {doc_info['difficulty_level']}")
        print(f"   • Reading time: {doc_info['estimated_reading_time']} minutes")
        
        print(f"\n🔍 Key Concepts Identified:")
        for concept in doc_info['key_concepts'][:10]:
            print(f"   • {concept}")
        
        print(f"\n🎯 Learning Objectives:")
        for objective in doc_info['learning_objectives'][:5]:
            print(f"   • {objective}")
        
        structure = content_data["structure"]
        print(f"\n📋 Document Structure:")
        print(f"   • Total lines: {structure['total_lines']}")
        print(f"   • Headings found: {len(structure['headings'])}")
        print(f"   • Paragraphs: {structure['paragraphs']}")
        print(f"   • Lists: {len(structure['lists'])}")
        
        if structure['headings']:
            print(f"\n📑 Document Outline:")
            for heading in structure['headings'][:5]:
                print(f"   {heading['level']}. {heading['text']}")
        
        print(f"\n📝 Content Chunks: {len(content_data['chunks'])} chunks created")
        
    except Exception as e:
        print(f"❌ Error in document analysis: {e}")
    
    finally:
        # Cleanup
        import os
        if os.path.exists("complex_neural_networks.txt"):
            os.remove("complex_neural_networks.txt")


def example_personality_adaptation():
    """Example of personality adaptation features"""
    
    client = MinervaClient()
    
    print("\n🧠 Personality Adaptation Example")
    print("=" * 35)
    
    session_token = client.create_session(1)
    
    # Simulate different conversation styles
    conversations = [
        ("Can you explain neural networks?", "learning"),
        ("I prefer detailed explanations with examples.", "learning"),
        ("That's fascinating! Can you tell me more about backpropagation?", "learning"),
        ("I learn best when I can see step-by-step breakdowns.", "learning"),
        ("Could you provide a comprehensive overview of CNNs?", "learning"),
    ]
    
    print("Simulating conversation to demonstrate adaptation...")
    
    for i, (message, context) in enumerate(conversations, 1):
        print(f"\n{i}. User: {message}")
        
        response = client.chat(message, 1, session_token, context)
        print(f"   🤖 Minerva: {response['content'][:100]}...")
        
        if response.get('learning_insights'):
            insights = response['learning_insights']
            if insights:
                print(f"   📊 Learning insights: {insights}")
    
    # Trigger personality analysis
    print("\n🔍 Analyzing conversation patterns...")
    try:
        analysis_response = client.session.post(
            f"{client.base_url}/api/v1/users/1/sessions/{session_token}/analyze-personality"
        )
        analysis_response.raise_for_status()
        analysis = analysis_response.json()
        
        print("✅ Personality analysis completed!")
        
        if analysis.get('adaptations_found'):
            adaptations = analysis['adaptations_found']
            print(f"\n🎯 Detected Adaptations:")
            for key, value in adaptations.items():
                if key != 'analysis_timestamp' and key != 'message_count_analyzed':
                    print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        if analysis.get('insights_applied'):
            insights = analysis['insights_applied']
            print(f"\n💡 Applied Insights:")
            for key, value in insights.items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
    
    except Exception as e:
        print(f"⚠️  Personality analysis not available: {e}")
    
    # Get personalized recommendations
    try:
        rec_response = client.session.get(
            f"{client.base_url}/api/v1/users/1/learning-recommendations"
        )
        rec_response.raise_for_status()
        recommendations = rec_response.json()
        
        print(f"\n🎨 Personalized Recommendations:")
        story_prefs = recommendations['recommendations']['story_preferences']
        print(f"   Story style: {story_prefs}")
        
        learning_approach = recommendations['recommendations']['learning_approach']
        print(f"   Learning approach: {learning_approach}")
    
    except Exception as e:
        print(f"⚠️  Recommendations not available: {e}")


if __name__ == "__main__":
    print("Minerva Learning Engine - API Examples")
    print("=====================================")
    
    try:
        # Run complete learning journey example
        example_complete_learning_journey()
        
        # Run document analysis example
        example_document_analysis()
        
        # Run personality adaptation example
        example_personality_adaptation()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to Minerva API")
        print("Make sure the FastAPI server is running:")
        print("   uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Examples completed!")
    print("Visit http://localhost:8000/docs for interactive API documentation")