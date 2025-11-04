"""Information extraction pipeline for meeting intelligence."""
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.models.adapter import ModelAdapter
from app.preprocessing.parser import TranscriptSegment
from app.preprocessing.cleaner import TranscriptCleaner


class MeetingExtractor:
    """Extract structured information from meeting transcripts."""
    
    # Decision keywords
    DECISION_KEYWORDS = {
        'decided', 'decision', 'agreed', 'approved', 'concluded',
        'resolved', 'settled', 'chosen', 'voted', 'agreement'
    }
    
    # Risk keywords
    RISK_KEYWORDS = {
        'risk', 'concern', 'issue', 'problem', 'blocker', 'blocking',
        'challenge', 'threat', 'warning', 'caution', 'danger', 'worry'
    }
    
    # Priority keywords
    PRIORITY_KEYWORDS = {
        'high': ['urgent', 'critical', 'important', 'asap', 'immediately', 'priority'],
        'medium': ['moderate', 'standard', 'normal'],
        'low': ['low priority', 'when possible', 'nice to have']
    }
    
    def __init__(self, model_adapter: ModelAdapter, cleaner: Optional[TranscriptCleaner] = None):
        """Initialize extractor with model adapter and optional cleaner."""
        self.model_adapter = model_adapter
        self.cleaner = cleaner or TranscriptCleaner()
    
    def chunk_text(self, text: str, max_tokens: int = 1000) -> List[str]:
        """Split text into chunks that fit within model context window."""
        # Simple word-based chunking (roughly 1 token ≈ 0.75 words)
        max_words = int(max_tokens * 0.75)
        words = text.split()
        chunks = []
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word.split())
            if current_length + word_length > max_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def extract_summary(self, segments: List[TranscriptSegment]) -> str:
        """Generate meeting summary using the model adapter."""
        # Combine segments into full text
        full_text = ' '.join([seg.text for seg in segments])
        
        # Chunk if necessary (BART models typically handle 1024 tokens)
        chunks = self.chunk_text(full_text, max_tokens=1000)
        
        if len(chunks) == 1:
            # Single chunk - direct summarization
            summary = self.model_adapter.summarize(
                chunks[0],
                max_length=150,
                min_length=50
            )
        else:
            # Multiple chunks - summarize each, then summarize summaries
            partial_summaries = []
            for chunk in chunks:
                chunk_summary = self.model_adapter.summarize(
                    chunk,
                    max_length=100,
                    min_length=30
                )
                partial_summaries.append(chunk_summary)
            
            # Summarize the combined partial summaries
            combined_summary_text = ' '.join(partial_summaries)
            summary = self.model_adapter.summarize(
                combined_summary_text,
                max_length=150,
                min_length=50
            )
        
        return summary
    
    def create_extraction_prompt(self, summary: str) -> str:
        """Create prompt for structured extraction using instruction-tuned models."""
        prompt = f"""You are a meeting intelligence extractor. Extract structured insights from the following meeting summary in JSON format.

Required JSON schema:
{{
  "decisions": [{{"text": "decision text", "speaker": "name or null", "confidence": 0.0-1.0}}],
  "action_items": [{{"action": "action text", "owner": "name or null", "due_date": "date or null", "priority": "high|medium|low", "confidence": 0.0-1.0}}],
  "risks": [{{"risk": "risk description", "mentioned_by": "name or null", "confidence": 0.0-1.0}}]
}}

Confidence scoring:
- High (0.9): Explicitly stated ("John will do X", "We decided to Y")
- Medium (0.7): Implied or suggested ("We should do X", "Someone needs to")
- Low (0.4): Ambiguous or uncertain ("Maybe we could", "Perhaps")

Meeting Summary:
{summary}

Extract and return ONLY valid JSON. Do not include any explanatory text outside the JSON."""
        
        return prompt
    
    def extract_structured_data(self, summary: str, segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract structured decisions, actions, and risks from summary."""
        # First, try using the model adapter's extraction capabilities
        # For models that support structured generation, use the prompt
        prompt = self.create_extraction_prompt(summary)
        
        # Use model to generate structured output
        # Note: For local models, we'll use a text generation approach
        # For now, implement rule-based extraction as fallback
        # In production, this would use an instruction-tuned model
        
        decisions = self._extract_decisions(summary, segments)
        action_items = self._extract_action_items(summary, segments)
        risks = self._extract_risks(summary, segments)
        
        return {
            "decisions": decisions,
            "action_items": action_items,
            "risks": risks
        }
    
    def _extract_decisions(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions using rule-based and model-based approaches."""
        decisions = []
        summary_lower = summary.lower()
        
        # Find segments with decision keywords
        for seg in segments:
            text_lower = seg.text.lower()
            if any(keyword in text_lower for keyword in self.DECISION_KEYWORDS):
                # Calculate confidence
                if any(explicit in text_lower for explicit in ['decided', 'agreed', 'approved']):
                    confidence = 0.9
                elif any(suggestive in text_lower for suggestive in ['should', 'need to', 'will']):
                    confidence = 0.7
                else:
                    confidence = 0.5
                
                decisions.append({
                    "text": seg.text,
                    "speaker": seg.speaker,
                    "timestamp": seg.timestamp,
                    "confidence": confidence
                })
        
        return decisions
    
    def _extract_action_items(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items with owners and due dates."""
        action_items = []
        summary_lower = summary.lower()
        
        # Extract from segments
        for seg in segments:
            text_lower = seg.text.lower()
            
            # Look for assignment patterns
            assignment_patterns = [
                r'(\w+)\s+will\s+(.+?)(?:\.|$)',
                r'(\w+)\s+should\s+(.+?)(?:\.|$)',
                r'assigned\s+to\s+(\w+).*?to\s+(.+?)(?:\.|$)',
                r'(\w+)\s+to\s+(.+?)(?:\.|$)',
            ]
            
            owner = None
            action = None
            
            for pattern in assignment_patterns:
                match = re.search(pattern, seg.text, re.IGNORECASE)
                if match:
                    owner = match.group(1)
                    action = match.group(2).strip()
                    break
            
            # Also check for "we/team will" patterns
            if not owner:
                if re.search(r'(?:we|team|I)\s+will\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE):
                    match = re.search(r'(?:we|team|I)\s+will\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                    action = match.group(1).strip() if match else None
                    owner = seg.speaker  # Use speaker as owner
            
            # Extract due date patterns
            due_date = None
            date_patterns = [
                r'by\s+(\w+\s+\d{1,2})',
                r'due\s+(.+?)(?:\.|$)',
                r'(\w+day)',
                r'next\s+week',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, seg.text, re.IGNORECASE)
                if due_date:
                    break
                if match:
                    due_date = match.group(1)
            
            # Determine priority
            priority = "medium"
            text_for_priority = action or seg.text.lower()
            if any(p in text_for_priority for p in self.PRIORITY_KEYWORDS['high']):
                priority = "high"
            elif any(p in text_for_priority for p in self.PRIORITY_KEYWORDS['low']):
                priority = "low"
            
            # Calculate confidence
            confidence = self.cleaner.calculate_assignment_confidence(seg.text)
            
            if action or owner:
                action_items.append({
                    "action": action or seg.text,
                    "owner": owner,
                    "due_date": due_date,
                    "priority": priority,
                    "confidence": confidence
                })
        
        return action_items
    
    def _extract_risks(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks and blockers."""
        risks = []
        
        for seg in segments:
            text_lower = seg.text.lower()
            if any(keyword in text_lower for keyword in self.RISK_KEYWORDS):
                # Determine confidence based on explicitness
                if any(explicit in text_lower for explicit in ['risk', 'blocker', 'problem', 'issue']):
                    confidence = 0.85
                elif any(suggestive in text_lower for suggestive in ['concern', 'worry', 'challenge']):
                    confidence = 0.7
                else:
                    confidence = 0.5
                
                risks.append({
                    "risk": seg.text,
                    "mentioned_by": seg.speaker,
                    "confidence": confidence
                })
        
        return risks
    
    def process(self, segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Full extraction pipeline."""
        # Generate summary
        summary = self.extract_summary(segments)
        
        # Extract structured data
        structured = self.extract_structured_data(summary, segments)
        
        # Get metadata
        speakers = list(set([seg.speaker for seg in segments if seg.speaker]))
        
        return {
            "summary": summary,
            "decisions": structured["decisions"],
            "action_items": structured["action_items"],
            "risks": structured["risks"],
            "metadata": {
                "speakers": speakers,
                "segment_count": len(segments),
                "extracted_at": datetime.utcnow().isoformat()
            }
        }
