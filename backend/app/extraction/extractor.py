"""Information extraction pipeline for meeting intelligence."""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.adapter import ModelAdapter
from app.preprocessing.parser import TranscriptSegment
from app.preprocessing.cleaner import TranscriptCleaner
from app.extraction.specialized_extractors import (
    IntentTagger, DecisionExtractor, ActionExtractor, RiskExtractor
)


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
    
    # Action verbs
    ACTION_VERBS = {
        'will', 'should', 'need to', 'must', 'going to', 'plan to',
        'assigned', 'responsible', 'handle', 'complete', 'review', 'follow up'
    }
    
    def __init__(self, model_adapter: ModelAdapter, cleaner: Optional[TranscriptCleaner] = None):
        """Initialize extractor with model adapter and optional cleaner."""
        self.model_adapter = model_adapter
        self.cleaner = cleaner or TranscriptCleaner()
        self._embedding_model = None
        self._summary_embedding = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model for confidence scoring."""
        if self._embedding_model is None:
            # Try to get embedding model from cleaner if available
            if hasattr(self.cleaner, 'embedding_model') and self.cleaner.embedding_model:
                self._embedding_model = self.cleaner.embedding_model
            else:
                # Try to get from model adapter if hybrid
                if hasattr(self.model_adapter, 'get_embedding_model'):
                    try:
                        self._embedding_model = self.model_adapter.get_embedding_model()
                    except:
                        pass
        return self._embedding_model
    
    def extract_summary(self, segments: List[TranscriptSegment]) -> str:
        """Generate meeting summary using hierarchical summarization (500-700 token chunks)."""
        # Combine segments into full text
        full_text = ' '.join([seg.text for seg in segments])
        
        # Use semantic chunking if available (500-700 tokens per chunk)
        if hasattr(self.cleaner, 'semantic_chunk'):
            chunks = self.cleaner.semantic_chunk(full_text, max_tokens=650, min_tokens=300)
        else:
            # Fallback to simple chunking
            chunks = self._chunk_text_simple(full_text, max_tokens=650)
        
        if len(chunks) == 1:
            # Single chunk - try direct summarization with fallback
            try:
                summary = self.model_adapter.summarize(
                    chunks[0],
                    max_length=200,
                    min_length=80
                )
            except RuntimeError as e:
                # If model fails (e.g., input too long), fall back to chunking
                if "index out of range" in str(e).lower() or "too long" in str(e).lower():
                    chunks = self._chunk_text_simple(chunks[0], max_tokens=500)
                    return self._hierarchical_summarize(chunks)
                raise
        else:
            # Multiple chunks - hierarchical summarization
            summary = self._hierarchical_summarize(chunks)
        
        # Store summary embedding for confidence scoring
        self._cache_summary_embedding(summary)
        
        return summary
    
    def _hierarchical_summarize(self, chunks: List[str]) -> str:
        """Perform hierarchical summarization: chunk-level then meta-level."""
        partial_summaries = []
        
        for i, chunk in enumerate(chunks):
            # Skip empty chunks
            if not chunk or not chunk.strip():
                continue
            
            try:
                # Chunk-level summarization (more detailed)
                chunk_summary = self.model_adapter.summarize(
                    chunk,
                    max_length=120,
                    min_length=40
                )
                if chunk_summary and chunk_summary.strip():
                    partial_summaries.append(chunk_summary)
            except RuntimeError as e:
                # If chunk is still too long, try smaller chunking
                if "index out of range" in str(e).lower() or "too long" in str(e).lower():
                    # Recursively chunk this chunk
                    sub_chunks = self._chunk_text_simple(chunk, max_tokens=400)
                    for sub_chunk in sub_chunks:
                        try:
                            sub_summary = self.model_adapter.summarize(
                                sub_chunk,
                                max_length=80,
                                min_length=25
                            )
                            if sub_summary and sub_summary.strip():
                                partial_summaries.append(sub_summary)
                        except:
                            continue
                else:
                    # Other error, continue with next chunk
                    continue
        
        # Meta-summarization: combine all chunk summaries
        if not partial_summaries:
            return "Unable to generate summary due to processing errors."
        
        combined_summary_text = ' '.join(partial_summaries)
        if not combined_summary_text.strip():
            return "Unable to generate summary. No valid summaries were extracted from chunks."
        
        # If combined text is still too long, chunk it again
        if len(combined_summary_text) > 4000:  # Rough estimate for 1000 tokens
            meta_chunks = self._chunk_text_simple(combined_summary_text, max_tokens=800)
            meta_summaries = []
            for meta_chunk in meta_chunks:
                try:
                    meta_sum = self.model_adapter.summarize(
                        meta_chunk,
                        max_length=100,
                        min_length=30
                    )
                    if meta_sum and meta_sum.strip():
                        meta_summaries.append(meta_sum)
                except:
                    continue
            combined_summary_text = ' '.join(meta_summaries) if meta_summaries else combined_summary_text
        
        # Final meta-summarization
        try:
            # Create a more structured summary prompt
            summary_prompt = f"""Create a comprehensive meeting summary with this structure:

OPENING: Start with "[Meeting duration]-minute [meeting type] session focused on [main topic]". Estimate duration from discussion length and meeting type from content.

KEY OUTCOMES: In one paragraph, list the most important decisions and changes, including:
- Specific dates and deadlines mentioned
- Quantitative metrics (counts, numbers, percentages)
- Major decisions with before/after states (e.g., "pushed launch from X to Y")
- Final determinations on features or scope

MEETING COVERAGE: Summarize what was discussed in detail:
- Current status reviews with specific issues or flags mentioned
- Feature decisions with specific counts (e.g., "10 core features, cut 4")
- Strategy discussions and approaches chosen
- Risk assessments with categories and priorities
- Action item assignments with owners and deadlines
- Dependencies and contingency planning

Meeting discussion:
{combined_summary_text}

Create a 2-3 paragraph professional executive summary that captures all key information:"""
            
            summary = self.model_adapter.summarize(
                summary_prompt if len(combined_summary_text) < 2000 else combined_summary_text,
                max_length=250,
                min_length=100
            )
        except:
            # If meta-summarization fails, return combined summaries
            summary = combined_summary_text
        
        # Clean up summary - remove extra whitespace and ensure proper formatting
        summary = re.sub(r'\s+', ' ', summary).strip()
        # Ensure sentences end properly
        summary = re.sub(r'\.\s+\.', '.', summary)
        
        return summary
    
    def _chunk_text_simple(self, text: str, max_tokens: int = 650) -> List[str]:
        """Simple word-based chunking fallback."""
        max_words = int(max_tokens * 0.75)
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + 1 > max_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = 1
            else:
                current_chunk.append(word)
                current_length += 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _cache_summary_embedding(self, summary: str):
        """Cache summary embedding for confidence scoring."""
        embedding_model = self._get_embedding_model()
        if embedding_model:
            try:
                self._summary_embedding = embedding_model.encode([summary])[0]
            except:
                self._summary_embedding = None
    
    def _calculate_semantic_confidence(self, text: str) -> float:
        """Calculate confidence using semantic similarity to summary."""
        embedding_model = self._get_embedding_model()
        if not embedding_model or self._summary_embedding is None:
            # Fallback to enhanced keyword-based confidence
            return self._calculate_keyword_confidence(text)
        
        try:
            text_embedding = embedding_model.encode([text])[0]
            similarity = cosine_similarity(
                [self._summary_embedding],
                [text_embedding]
            )[0][0]
            
            # Base confidence from similarity
            if similarity > 0.7:
                base_confidence = 0.9
            elif similarity > 0.5:
                base_confidence = 0.7
            elif similarity > 0.3:
                base_confidence = 0.5
            else:
                base_confidence = 0.4
            
            # Boost confidence for quantitative data
            quantitative_boost = self._calculate_quantitative_boost(text)
            return min(base_confidence + quantitative_boost, 0.95)
            
        except:
            return self._calculate_keyword_confidence(text)
    
    def _calculate_quantitative_boost(self, text: str) -> float:
        """Calculate confidence boost based on quantitative data presence."""
        boost = 0.0
        
        # Check for dates
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b(?:next|this|last)\s+(?:week|month|quarter)',
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
            r'\bQ[1-4]\b'
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns):
            boost += 0.1
        
        # Check for numbers and counts
        number_patterns = [
            r'\b\d+\s*(?:features?|items?|risks?|decisions?|actions?)\b',
            r'\b\d+%\b',
            r'\$\d+(?:K|M|B)?',
            r'\b\d+\s*(?:days?|weeks?|months?|hours?)',
            r'\b(?:first|second|third|fourth|fifth|\d+)\s+(?:phase|stage|step)',
            r'\b\d+\s*(?:core|additional|total)'
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in number_patterns):
            boost += 0.1
        
        # Check for before/after comparisons
        comparison_patterns = [
            r'(?:from|change|push|move|shift)\s+.+\s+to\s+',
            r'(?:instead of|rather than|versus|vs\.?)\s+',
            r'(?:increase|decrease|reduce|expand)\s+(?:from|by|to)\s*\d+'
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in comparison_patterns):
            boost += 0.05
        
        return boost
    
    def _calculate_keyword_confidence(self, text: str) -> float:
        """Enhanced keyword-based confidence calculation."""
        text_lower = text.lower()
        confidence = 0.5  # base confidence
        
        # Check for explicit decision language
        if any(explicit in text_lower for explicit in ['will', 'decided', 'agreed', 'must', 'approved', 'finalized']):
            confidence = 0.9
        elif any(suggestive in text_lower for suggestive in ['should', 'might', 'could', 'consider', 'propose']):
            confidence = 0.7
        
        # Apply quantitative boost
        confidence += self._calculate_quantitative_boost(text)
        
        return min(confidence, 0.95)
    
    def extract_structured_data(self, summary: str, segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract structured decisions, actions, and risks using enhanced extractors."""
        # Get embedding model for potential use
        embedding_model = self._get_embedding_model()
        
        # Use enhanced specialized extractors that process full context
        decision_extractor = DecisionExtractor(self.model_adapter, embedding_model)
        action_extractor = ActionExtractor(self.model_adapter, embedding_model)
        risk_extractor = RiskExtractor(self.model_adapter, embedding_model)
        
        # Extract with enhanced extractors - pass empty tagged_sentences to use full context
        decisions = decision_extractor.extract([], segments)
        action_items = action_extractor.extract([], segments)
        risks = risk_extractor.extract([], segments)
        
        # Step 4: Filter low confidence items - but be more lenient
        # Only filter out very low confidence items (< 0.4) to catch more content
        print(f"[DEBUG] Extractor: Before filtering - {len(decisions)} decisions, {len(action_items)} actions, {len(risks)} risks")
        decisions = [d for d in decisions if d.get("confidence", 0) >= 0.4]
        action_items = [a for a in action_items if a.get("confidence", 0) >= 0.4]
        risks = [r for r in risks if r.get("confidence", 0) >= 0.4]
        print(f"[DEBUG] Extractor: After filtering - {len(decisions)} decisions, {len(action_items)} actions, {len(risks)} risks")
        
        # Transform Ollama output format to match frontend expectations
        transformed_decisions = self._transform_decisions_for_frontend(decisions)
        transformed_actions = self._transform_actions_for_frontend(action_items)
        transformed_risks = self._transform_risks_for_frontend(risks)
        print(f"[DEBUG] Extractor: After transformation - {len(transformed_decisions)} decisions, {len(transformed_actions)} actions, {len(transformed_risks)} risks")
        
        return {
            "decisions": transformed_decisions,
            "action_items": transformed_actions,
            "risks": transformed_risks
        }
    
    def _extract_decisions(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions using rule-based, NER, and semantic approaches."""
        decisions = []
        summary_lower = summary.lower()
        
        # Extract entities from summary for better speaker identification
        entities = []
        try:
            entities = self.model_adapter.extract_entities(summary)
        except:
            pass
        
        # Build entity map (person names)
        person_entities = {}
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('entity_group', entity.get('label', ''))
                    if entity_type in ['PER', 'PERSON']:
                        person_entities[entity.get('word', '').lower()] = entity.get('word', '')
        
        # Find segments with decision keywords
        for seg in segments:
            text_lower = seg.text.lower()
            if any(keyword in text_lower for keyword in self.DECISION_KEYWORDS):
                # Use semantic confidence
                confidence = self._calculate_semantic_confidence(seg.text)
                
                # Try to identify speaker from NER if not already identified
                speaker = seg.speaker
                if not speaker:
                    # Check if any person entities are in the segment
                    for person_lower, person_original in person_entities.items():
                        if person_lower in text_lower:
                            speaker = person_original
                            break
                
                decisions.append({
                    "text": seg.text,
                    "speaker": speaker,
                    "timestamp": seg.timestamp,
                    "confidence": confidence
                })
        
        return decisions
    
    def _extract_action_items(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items with owners and due dates using NER and pattern matching."""
        action_items = []
        
        # Extract entities from summary
        entities = []
        try:
            entities = self.model_adapter.extract_entities(summary)
        except:
            pass
        
        # Build entity maps
        person_entities = {}
        org_entities = {}
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('entity_group', entity.get('label', ''))
                    word = entity.get('word', '')
                    if entity_type in ['PER', 'PERSON']:
                        person_entities[word.lower()] = word
                    elif entity_type in ['ORG', 'ORGANIZATION']:
                        org_entities[word.lower()] = word
        
        # Extract from segments
        for seg in segments:
            text_lower = seg.text.lower()
            
            # Check if segment contains action verbs
            has_action = any(verb in text_lower for verb in self.ACTION_VERBS)
            if not has_action:
                continue
            
            # Look for assignment patterns
            owner = seg.speaker  # Default to segment speaker
            action = None
            
            # Pattern 1: "Person will do X"
            pattern1 = re.search(r'(\w+(?:\s+\w+)?)\s+will\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
            if pattern1:
                owner_candidate = pattern1.group(1)
                action = pattern1.group(2).strip()
                # Verify if it's a person name (check against NER entities or common patterns)
                if owner_candidate.lower() in person_entities or self._looks_like_name(owner_candidate):
                    owner = person_entities.get(owner_candidate.lower(), owner_candidate)
            
            # Pattern 2: "assigned to Person"
            if not owner or owner == seg.speaker:
                pattern2 = re.search(r'assigned\s+to\s+(\w+(?:\s+\w+)?)', seg.text, re.IGNORECASE)
                if pattern2:
                    owner_candidate = pattern2.group(1)
                    owner = person_entities.get(owner_candidate.lower(), owner_candidate)
                    # Extract action text
                    action_match = re.search(r'to\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                    if action_match:
                        action = action_match.group(1).strip()
            
            # Pattern 3: "we/team/I will do X"
            if not action:
                pattern3 = re.search(r'(?:we|team|I|the\s+team)\s+will\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                if pattern3:
                    action = pattern3.group(1).strip()
                    owner = owner or seg.speaker or "Team"
            
            # Pattern 4: "Person should/needs to do X"
            if not owner or owner == seg.speaker:
                pattern4 = re.search(r'(\w+(?:\s+\w+)?)\s+(?:should|needs? to|must)\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                if pattern4:
                    owner_candidate = pattern4.group(1)
                    action = pattern4.group(2).strip()
                    if owner_candidate.lower() in person_entities or self._looks_like_name(owner_candidate):
                        owner = person_entities.get(owner_candidate.lower(), owner_candidate)
            
            # If no action extracted but has action verbs, use segment text
            if not action:
                action = seg.text
            
            # Extract due date patterns
            due_date = None
            date_patterns = [
                r'by\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\w+)?)',
                r'due\s+(.+?)(?:\.|$)',
                r'(\w+day)',
                r'next\s+week',
                r'end\s+of\s+(\w+)',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, seg.text, re.IGNORECASE)
                if match:
                    due_date = match.group(1) if match.groups() else match.group(0)
                    break
            
            # Determine priority
            priority = "medium"
            text_for_priority = action.lower() if action else text_lower
            if any(p in text_for_priority for p in self.PRIORITY_KEYWORDS['high']):
                priority = "high"
            elif any(p in text_for_priority for p in self.PRIORITY_KEYWORDS['low']):
                priority = "low"
            
            # Calculate semantic confidence
            confidence = self._calculate_semantic_confidence(action if action else seg.text)
            
            action_items.append({
                "action": action or seg.text,
                "owner": owner,
                "due_date": due_date,
                "priority": priority,
                "confidence": confidence
            })
        
        return action_items
    
    def _looks_like_name(self, text: str) -> bool:
        """Heuristic to check if text looks like a person name."""
        # Capitalized first letter, 2-3 words, not common words
        words = text.split()
        if len(words) < 1 or len(words) > 3:
            return False
        if words[0][0].isupper() and len(words[0]) > 1:
            return True
        return False
    
    def _extract_risks(self, summary: str, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks and blockers using semantic confidence."""
        risks = []
        
        # Extract entities for better speaker identification
        entities = []
        try:
            entities = self.model_adapter.extract_entities(summary)
        except:
            pass
        
        person_entities = {}
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('entity_group', entity.get('label', ''))
                    if entity_type in ['PER', 'PERSON']:
                        person_entities[entity.get('word', '').lower()] = entity.get('word', '')
        
        for seg in segments:
            text_lower = seg.text.lower()
            if any(keyword in text_lower for keyword in self.RISK_KEYWORDS):
                # Use semantic confidence
                confidence = self._calculate_semantic_confidence(seg.text)
                
                # Try to identify speaker from NER
                mentioned_by = seg.speaker
                if not mentioned_by:
                    for person_lower, person_original in person_entities.items():
                        if person_lower in text_lower:
                            mentioned_by = person_original
                            break
                
                risks.append({
                    "risk": seg.text,
                    "mentioned_by": mentioned_by,
                    "confidence": confidence
                })
        
        return risks
    
    def _calculate_quality_metrics(self, summary: str, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality metrics for the extraction."""
        metrics = {
            "summary_length": len(summary),
            "decisions_count": len(extracted.get("decisions", [])),
            "actions_count": len(extracted.get("action_items", [])),
            "risks_count": len(extracted.get("risks", [])),
            "avg_confidence": 0.0
        }
        
        # Calculate average confidence
        all_items = (
            extracted.get("decisions", []) +
            extracted.get("action_items", []) +
            extracted.get("risks", [])
        )
        if all_items:
            confidences = [item.get("confidence", 0.5) for item in all_items]
            metrics["avg_confidence"] = sum(confidences) / len(confidences)
        
        # Calculate redundancy ratio (simple heuristic)
        summary_words = set(summary.lower().split())
        if len(summary_words) > 0:
            # Check for repeated phrases (simple check)
            summary_sentences = re.split(r'[.!?]+', summary)
            unique_sentences = set(s.lower().strip() for s in summary_sentences if s.strip())
            if len(summary_sentences) > 0:
                metrics["redundancy_ratio"] = 1 - (len(unique_sentences) / len(summary_sentences))
            else:
                metrics["redundancy_ratio"] = 0.0
        else:
            metrics["redundancy_ratio"] = 0.0
        
        return metrics
    
    def _extract_metadata(self, segments: List[TranscriptSegment], summary: str, structured: Dict[str, Any]) -> Dict[str, Any]:
        """Extract meeting metadata for enhanced summary generation."""
        metadata = {}
        
        # Estimate meeting duration based on discussion depth
        segment_count = len(segments)
        avg_segment_length = sum(len(seg.text.split()) for seg in segments) / len(segments) if segments else 0
        
        # Rough duration estimate
        if segment_count > 100 or avg_segment_length > 50:
            metadata["duration"] = "60"
        elif segment_count > 50:
            metadata["duration"] = "45"
        elif segment_count > 20:
            metadata["duration"] = "30"
        else:
            metadata["duration"] = "15"
        
        # Detect meeting type from content
        summary_lower = summary.lower()
        if "planning" in summary_lower or "plan" in summary_lower:
            metadata["meeting_type"] = "planning"
        elif "review" in summary_lower or "status" in summary_lower:
            metadata["meeting_type"] = "review"
        elif "retrospective" in summary_lower or "retro" in summary_lower:
            metadata["meeting_type"] = "retrospective"
        elif "strategy" in summary_lower or "strategic" in summary_lower:
            metadata["meeting_type"] = "strategic"
        else:
            metadata["meeting_type"] = "discussion"
        
        # Extract main topic from decisions or summary
        if structured["decisions"]:
            # Look for product/project names in decisions
            decision_text = " ".join([d.get("text", d.get("decision", "")) for d in structured["decisions"][:3]])
            if "launch" in decision_text.lower():
                metadata["main_topic"] = "product launch planning"
            elif "feature" in decision_text.lower():
                metadata["main_topic"] = "feature planning"
            elif "budget" in decision_text.lower():
                metadata["main_topic"] = "budget planning"
            else:
                metadata["main_topic"] = "project planning"
        else:
            metadata["main_topic"] = "team discussion"
        
        return metadata
    
    def _synthesize_executive_summary(self, initial_summary: str, structured: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Synthesize a coherent executive summary from extracted components."""
        # If Ollama adapter with structured data support
        if hasattr(self.model_adapter, 'extract_structured_data'):
            # Prepare structured data summary
            decisions_summary = []
            for d in structured["decisions"][:5]:  # Top 5 decisions
                decision_text = d.get("decision", d.get("text", ""))
                decisions_summary.append(f"- {decision_text}")
            
            actions_summary = []
            for a in structured["action_items"][:5]:  # Top 5 actions
                action_text = f"{a.get('owner', 'TBD')}: {a.get('action', '')}"
                if a.get('due_date'):
                    action_text += f" (by {a['due_date']})"
                actions_summary.append(f"- {action_text}")
            
            risks_summary = []
            for r in structured["risks"][:3]:  # Top 3 risks
                risk_text = r.get("risk", "")
                if r.get("impact"):
                    risk_text += f" ({r['impact']} impact)"
                risks_summary.append(f"- {risk_text}")
            
            synthesis_prompt = f"""Create a polished executive summary using this meeting analysis:

Initial Summary: {initial_summary}

Key Decisions Made:
{chr(10).join(decisions_summary) if decisions_summary else "No major decisions recorded"}

Action Items Assigned:
{chr(10).join(actions_summary) if actions_summary else "No action items recorded"}

Risks Identified:
{chr(10).join(risks_summary) if risks_summary else "No risks recorded"}

Meeting Type: {metadata.get('meeting_type', 'planning')} meeting
Estimated Duration: {metadata.get('duration', '45')} minutes
Main Topic: {metadata.get('main_topic', 'project planning')}

Create a 2-3 paragraph executive summary that:
1. Opens with "The [meeting type] was a [duration]-minute session focused on [main topic]"
2. Summarizes key outcomes including specific dates, numbers, and decisions
3. Highlights critical next steps and risks
4. Uses professional, concise language

Executive Summary:"""
            
            try:
                synthesized = self.model_adapter.summarize(
                    synthesis_prompt,
                    max_length=300,
                    min_length=150
                )
                return synthesized.strip()
            except Exception as e:
                print(f"Synthesis failed: {e}, using initial summary")
                return initial_summary
        
        # Fallback: enhance initial summary with key points
        key_points = []
        if structured["decisions"]:
            key_points.append(f"{len(structured['decisions'])} decisions made")
        if structured["action_items"]:
            key_points.append(f"{len(structured['action_items'])} action items assigned")
        if structured["risks"]:
            key_points.append(f"{len(structured['risks'])} risks identified")
        
        enhanced = f"This {metadata.get('duration', '45')}-minute {metadata.get('meeting_type', 'planning')} session focused on {metadata.get('main_topic', 'project planning')}. "
        enhanced += initial_summary
        if key_points:
            enhanced += f" Key outcomes: {', '.join(key_points)}."
        
        return enhanced
    
    def process(self, segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Full extraction pipeline with quality detection and synthesis."""
        # Generate initial summary
        initial_summary = self.extract_summary(segments)
        
        # Extract structured data
        structured = self.extract_structured_data(initial_summary, segments)
        
        # Extract metadata
        metadata = self._extract_metadata(segments, initial_summary, structured)
        
        # Synthesize executive summary if we have good extraction results
        if (len(structured["decisions"]) > 0 or len(structured["action_items"]) > 0):
            summary = self._synthesize_executive_summary(
                initial_summary, structured, metadata
            )
        else:
            summary = initial_summary
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(summary, structured)
        
        # Determine if quality is low and might need fallback
        quality_low = (
            quality_metrics["redundancy_ratio"] > 0.3 or
            quality_metrics["decisions_count"] + quality_metrics["actions_count"] < 5 or
            quality_metrics["avg_confidence"] < 0.5
        )
        
        # Get speakers
        speakers = list(set([seg.speaker for seg in segments if seg.speaker]))
        
        return {
            "summary": summary,
            "decisions": structured["decisions"],
            "action_items": structured["action_items"],
            "risks": structured["risks"],
            "quality_metrics": quality_metrics,
            "quality_warning": quality_low,
            "metadata": {
                "speakers": speakers,
                "segment_count": len(segments),
                "meeting_type": metadata.get("meeting_type", "meeting"),
                "duration_estimate": metadata.get("duration", "45"),
                "main_topic": metadata.get("main_topic", "project discussion"),
                "extracted_at": datetime.utcnow().isoformat()
            }
        }
    
    def _transform_decisions_for_frontend(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Ollama decision format to frontend expected format."""
        transformed = []
        for decision in decisions:
            # Ollama format: {"decision": "text", "participants": [...], "confidence": 0.9, "quantitative_data": {...}}
            # Frontend expects: {"text": "text", "speaker": "name", "timestamp": null, "confidence": 0.9}
            
            # Extract main speaker from participants
            participants = decision.get("participants", [])
            speaker = None
            if participants:
                # Use first participant as primary speaker
                if isinstance(participants, list) and len(participants) > 0:
                    speaker = participants[0]
                elif isinstance(participants, str):
                    speaker = participants
            
            transformed_decision = {
                "text": decision.get("decision", decision.get("text", "")),
                "speaker": speaker,
                "timestamp": None,  # Not available from Ollama
                "confidence": decision.get("confidence", 0.5),
                "rationale": decision.get("rationale")
            }
            
            # Include quantitative data if present
            if "quantitative_data" in decision:
                transformed_decision["quantitative_data"] = decision["quantitative_data"]
            
            transformed.append(transformed_decision)
        return transformed
    
    def _transform_actions_for_frontend(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform action items to frontend format with additional fields."""
        # Ensure all actions have required fields and preserve new fields
        transformed = []
        for action in actions:
            transformed_action = {
                "action": action.get("action", ""),
                "owner": action.get("owner", "Unknown"),
                "due_date": action.get("due_date"),
                "priority": action.get("priority", "medium"),
                "confidence": action.get("confidence", 0.5)
            }
            
            # Include optional fields if present
            if "dependencies" in action:
                transformed_action["dependencies"] = action["dependencies"]
            
            transformed.append(transformed_action)
        return transformed
    
    def _transform_risks_for_frontend(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Ollama risk format to frontend expected format."""
        transformed = []
        for risk in risks:
            # Frontend expects: {"risk": "text", "mentioned_by": "name", "confidence": 0.9}
            # This format should already match what Ollama returns
            transformed.append({
                "risk": risk.get("risk", ""),
                "category": risk.get("category"),
                "mentioned_by": risk.get("mentioned_by"),
                "confidence": risk.get("confidence", 0.5),
                "impact": risk.get("impact"),
                "mitigation": risk.get("mitigation"),
                "owner": risk.get("owner"),
                "priority": risk.get("priority")
            })
        return transformed
