import os
import re
from typing import Dict, List, Optional, Tuple
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
import logging

logger = logging.getLogger(__name__)


class ContentProcessor:
    def __init__(self):
        self.chunk_size = 1000  # Characters per chunk
        self.overlap_size = 200  # Overlap between chunks
    
    async def extract_content(self, file_path: str, file_type: str) -> Dict:
        """Extract content from uploaded file"""
        
        try:
            if file_type == 'pdf':
                content = await self._extract_pdf_content(file_path)
            elif file_type in ['docx', 'doc']:
                content = await self._extract_docx_content(file_path)
            elif file_type in ['txt', 'md']:
                content = await self._extract_text_content(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Process the extracted content
            processed_data = await self._process_content(content)
            
            return {
                "raw_content": content,
                "processed_content": processed_data["cleaned_content"],
                "content_structure": processed_data["structure"],
                "key_concepts": processed_data["concepts"],
                "learning_objectives": processed_data["objectives"],
                "difficulty_level": processed_data["difficulty"],
                "estimated_reading_time": processed_data["reading_time"],
                "chunks": processed_data["chunks"]
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract content: {str(e)}")
    
    async def _extract_pdf_content(self, file_path: str) -> str:
        """Extract text content from PDF file"""
        content = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
        except Exception as e:
            raise ValueError(f"Error reading PDF: {str(e)}")
        
        return content
    
    async def _extract_docx_content(self, file_path: str) -> str:
        """Extract text content from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
        except Exception as e:
            raise ValueError(f"Error reading DOCX: {str(e)}")
        
        return content
    
    async def _extract_text_content(self, file_path: str) -> str:
        """Extract content from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Unable to decode text file")
        except Exception as e:
            raise ValueError(f"Error reading text file: {str(e)}")
        
        return content
    
    async def _process_content(self, content: str) -> Dict:
        """Process and analyze the extracted content"""
        
        # Clean and normalize content
        cleaned_content = self._clean_content(content)
        
        # Analyze structure
        structure = self._analyze_structure(cleaned_content)
        
        # Extract key concepts (basic implementation)
        concepts = self._extract_key_concepts(cleaned_content)
        
        # Identify learning objectives (basic implementation)
        objectives = self._identify_learning_objectives(cleaned_content)
        
        # Estimate difficulty level
        difficulty = self._estimate_difficulty(cleaned_content)
        
        # Calculate reading time (average 200 words per minute)
        word_count = len(cleaned_content.split())
        reading_time = max(1, word_count // 200)
        
        # Create content chunks
        chunks = self._create_chunks(cleaned_content)
        
        return {
            "cleaned_content": cleaned_content,
            "structure": structure,
            "concepts": concepts,
            "objectives": objectives,
            "difficulty": difficulty,
            "reading_time": reading_time,
            "chunks": chunks
        }
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove special characters but keep basic punctuation
        content = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\']+', '', content)
        
        # Remove very short lines (likely artifacts)
        lines = content.split('\n')
        filtered_lines = [line.strip() for line in lines if len(line.strip()) > 3]
        
        return '\n'.join(filtered_lines)
    
    def _analyze_structure(self, content: str) -> Dict:
        """Analyze document structure"""
        lines = content.split('\n')
        structure = {
            "total_lines": len(lines),
            "headings": [],
            "sections": [],
            "lists": [],
            "paragraphs": 0
        }
        
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Detect headings (simple heuristic)
            if (len(line) < 100 and 
                (line.isupper() or 
                 re.match(r'^[A-Z][^\.]*$', line) or
                 re.match(r'^\d+\.?\s+[A-Z]', line))):
                structure["headings"].append({
                    "text": line,
                    "line_number": i + 1,
                    "level": self._estimate_heading_level(line)
                })
                current_section = line
            
            # Detect lists
            elif re.match(r'^[\-\*\+]\s+', line) or re.match(r'^\d+\.\s+', line):
                structure["lists"].append({
                    "text": line,
                    "line_number": i + 1,
                    "section": current_section
                })
            
            # Count paragraphs
            elif len(line) > 50:
                structure["paragraphs"] += 1
        
        return structure
    
    def _estimate_heading_level(self, heading: str) -> int:
        """Estimate heading level based on formatting"""
        if heading.isupper():
            return 1
        elif re.match(r'^\d+\.?\s+', heading):
            return 2
        else:
            return 3
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content (basic implementation)"""
        # This is a simple implementation - in production, you'd use NLP libraries
        
        # Find capitalized terms (potential concepts)
        concepts = set()
        
        # Extract capitalized phrases
        capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(capitalized_pattern, content)
        
        for match in matches:
            if len(match.split()) <= 3 and len(match) > 3:  # Not too long, not too short
                concepts.add(match)
        
        # Extract quoted terms
        quoted_pattern = r'"([^"]+)"'
        quoted_matches = re.findall(quoted_pattern, content)
        for match in quoted_matches:
            if len(match.split()) <= 3:
                concepts.add(match)
        
        # Filter common words
        common_words = {'The', 'This', 'That', 'These', 'Those', 'With', 'For', 'And', 'But', 'Or'}
        concepts = {c for c in concepts if c not in common_words}
        
        return list(concepts)[:20]  # Return top 20 concepts
    
    def _identify_learning_objectives(self, content: str) -> List[str]:
        """Identify potential learning objectives"""
        objectives = []
        
        # Look for objective-like patterns
        objective_patterns = [
            r'(?:learn|understand|master|explore|discover|analyze|evaluate|apply|create)\s+([^\.]+)',
            r'(?:objective|goal|aim|purpose):\s*([^\.]+)',
            r'(?:by the end|after reading|students will|learners will)\s+([^\.]+)'
        ]
        
        content_lower = content.lower()
        
        for pattern in objective_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10 and len(match.strip()) < 200:
                    objectives.append(match.strip().capitalize())
        
        return objectives[:10]  # Return top 10 objectives
    
    def _estimate_difficulty(self, content: str) -> str:
        """Estimate content difficulty level"""
        # Simple heuristic based on sentence complexity and vocabulary
        sentences = re.split(r'[\.!?]+', content)
        
        if not sentences:
            return "medium"
        
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Count complex words (more than 3 syllables - approximated by length)
        words = content.split()
        complex_words = sum(1 for word in words if len(word) > 8)
        complex_ratio = complex_words / len(words) if words else 0
        
        if avg_sentence_length > 25 or complex_ratio > 0.2:
            return "advanced"
        elif avg_sentence_length < 15 and complex_ratio < 0.1:
            return "beginner"
        else:
            return "intermediate"
    
    def _create_chunks(self, content: str) -> List[Dict]:
        """Create content chunks for processing"""
        chunks = []
        words = content.split()
        
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1  # +1 for space
            
            if current_length >= self.chunk_size:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "index": chunk_index,
                    "content": chunk_text,
                    "word_count": len(current_chunk),
                    "character_count": len(chunk_text)
                })
                
                # Start new chunk with overlap
                overlap_words = current_chunk[-self.overlap_size//5:]  # Rough overlap
                current_chunk = overlap_words
                current_length = sum(len(w) + 1 for w in overlap_words)
                chunk_index += 1
        
        # Add final chunk if there are remaining words
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "index": chunk_index,
                "content": chunk_text,
                "word_count": len(current_chunk),
                "character_count": len(chunk_text)
            })
        
        return chunks


content_processor = ContentProcessor()