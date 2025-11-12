"""Enhanced decision extractor implementing improvements from MIA_decisions_fix.md"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from app.models.adapter import ModelAdapter
from app.preprocessing.parser import TranscriptSegment


@dataclass
class EnhancedDecision:
    """Enhanced decision structure with thematic grouping."""
    title: str
    decision: str
    category: str
    participants: List[str]
    supporting_statements: List[str]
    quantitative_data: Dict[str, List[str]]
    confidence: float
    decision_type: str  # "explicit" or "implicit"


class EnhancedDecisionExtractor:
    """Enhanced decision extractor with semantic chunking, reasoning, and thematic grouping."""
    
    DECISION_EXTRACTION_PROMPT = """You are an expert meeting analyst. Extract and analyze DECISIONS from this meeting transcript.

Your task:
1. Identify all decisions, including implicit ones
2. Consolidate fragmented or repeated decisions  
3. Group decisions by themes
4. Infer decisions even when not explicitly stated

A DECISION is when participants:
- Agree on a course of action with specific outcomes
- Make a choice between options with clear results  
- Approve something with concrete details
- Set dates, deadlines, or quantitative targets
- Finalize scope, features, or deliverables
- Make changes to timelines, budgets, or scope

EXAMPLES of decisions (including implicit ones):
✅ EXPLICIT: "We decided to push the launch date from October 15th to October 29th"
✅ IMPLICIT: "Let's move the launch two weeks later" → Launch date change decision
✅ IMPLICIT: "We can't do all 15 features, let's focus on the core 10" → Feature scope decision
✅ IMPLICIT: "Marcus, escalate to security team and get external quotes" → Security audit approach decision
✅ IMPLICIT: "We need more buffer time between phases" → Timeline buffer decision

DECISION CATEGORIES:
- timeline: dates, deadlines, scheduling, delays
- features: scope, functionality, requirements
- budget: costs, allocations, financial decisions
- security: audits, compliance, risk mitigation
- communication: meetings, reporting, stakeholders
- resources: team assignments, tools, infrastructure
- process: workflows, procedures, methodologies
- other: miscellaneous decisions

REASONING PROCESS:
1. Read the entire transcript for context
2. Identify decision conversations across multiple speakers
3. Consolidate related statements into single decisions
4. Infer implicit decisions from context
5. Assign thematic categories
6. Create clear decision titles and summaries

{context}

Return in this EXACT JSON format:
{{
  "decisions": [
    {{
      "title": "short descriptive name (e.g., 'Launch Date Change', 'Feature Set Finalization')",
      "decision": "clear consolidated decision statement with specific details",
      "category": "timeline/features/budget/security/communication/resources/process/other",
      "participants": ["names of people involved in the decision"],
      "supporting_statements": ["key quotes that led to this decision"],
      "quantitative_data": {{
        "dates": ["specific dates mentioned"],
        "numbers": ["counts, amounts, metrics"],
        "changes": ["before/after comparisons"]
      }},
      "confidence": 0.9,
      "decision_type": "explicit/implicit"
    }}
  ]
}}

Consolidate related decisions and prioritize those with concrete outcomes.
Return ONLY valid JSON, no explanations."""

    DECISION_AGGREGATION_PROMPT = """Group and consolidate the following decisions into thematic categories:

{decisions}

Your task:
1. Merge similar or related decisions
2. Create high-level thematic groupings
3. Eliminate duplicates
4. Enhance decision titles for clarity

Return the grouped decisions with improved structure:
{{
  "grouped_decisions": [
    {{
      "theme": "Launch Date & Timeline",
      "decisions": [
        {{
          "title": "Launch Date Change",
          "decision": "consolidated decision with all relevant details",
          "category": "timeline",
          "participants": ["all relevant people"],
          "supporting_statements": ["merged key statements"],
          "quantitative_data": {{"consolidated data"}},
          "confidence": 0.95,
          "decision_type": "explicit"
        }}
      ]
    }}
  ]
}}"""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize enhanced decision extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions with enhanced semantic chunking and reasoning."""
        
        # Step 1: Create semantic chunks for better context processing
        semantic_chunks = self._create_semantic_chunks(all_segments)
        
        # Step 2: Extract raw decisions from each chunk
        raw_decisions = []
        for chunk in semantic_chunks:
            chunk_decisions = self._extract_chunk_decisions(chunk)
            raw_decisions.extend(chunk_decisions)
        
        # Step 3: Aggregate and deduplicate decisions
        aggregated_decisions = self._aggregate_decisions(raw_decisions)
        
        # Step 4: Enhance with thematic grouping and categorization
        final_decisions = self._enhance_decision_structure(aggregated_decisions)
        
        return final_decisions
    
    def _create_semantic_chunks(self, all_segments: List[TranscriptSegment], max_tokens: int = 800) -> List[List[TranscriptSegment]]:
        """Create semantic chunks optimized for decision extraction (500-1000 tokens)."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for segment in all_segments:
            # Estimate tokens (rough approximation: 1 token ≈ 0.75 words)
            segment_tokens = len(segment.text.split()) * 1.33
            
            # If adding this segment would exceed max_tokens, start new chunk
            if current_tokens + segment_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [segment]
                current_tokens = segment_tokens
            else:
                current_chunk.append(segment)
                current_tokens += segment_tokens
        
        # Add final chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Ensure we have at least one chunk
        return chunks if chunks else [all_segments]
    
    def _extract_chunk_decisions(self, chunk_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions from a semantic chunk using enhanced prompts."""
        context = self._build_extraction_context(chunk_segments)
        
        try:
            if hasattr(self.model_adapter, 'extract_structured_data'):
                response = self.model_adapter.extract_structured_data(
                    self.DECISION_EXTRACTION_PROMPT.format(context=context)
                )
                return response.get("decisions", [])
            else:
                # Fallback to pattern-based extraction with enhanced logic
                return self._extract_with_enhanced_patterns(chunk_segments)
        except Exception as e:
            print(f"Decision extraction failed: {e}")
            return []
    
    def _extract_with_enhanced_patterns(self, segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Enhanced pattern-based decision extraction with implicit detection."""
        decisions = []
        
        # Enhanced decision keywords including implicit patterns
        explicit_keywords = ['decided', 'decision', 'agreed', 'approved', 'concluded', 'finalized', 'settled']
        implicit_keywords = ['let\'s', 'we will', 'we\'re going to', 'push', 'move to', 'change to', 'focus on']
        timeline_keywords = ['deadline', 'by', 'before', 'after', 'schedule', 'delay', 'postpone']
        
        for i, seg in enumerate(segments):
            text_lower = seg.text.lower()
            
            # Check for decision patterns
            decision_score = 0
            decision_type = "explicit"
            
            # Explicit decision detection
            if any(kw in text_lower for kw in explicit_keywords):
                decision_score += 0.8
            
            # Implicit decision detection
            elif any(kw in text_lower for kw in implicit_keywords):
                decision_score += 0.6
                decision_type = "implicit"
            
            # Timeline decision detection
            elif any(kw in text_lower for kw in timeline_keywords):
                decision_score += 0.5
                decision_type = "implicit"
            
            if decision_score > 0.4:  # Threshold for considering as decision
                # Build context around this decision
                context_segments = segments[max(0, i-1):min(len(segments), i+2)]
                
                decision = {
                    "title": self._generate_decision_title(seg.text),
                    "decision": seg.text.strip(),
                    "category": self._categorize_decision(seg.text),
                    "participants": [seg.speaker] if seg.speaker else [],
                    "supporting_statements": [s.text for s in context_segments],
                    "quantitative_data": self._extract_quantitative_data(seg.text),
                    "confidence": min(decision_score, 1.0),
                    "decision_type": decision_type
                }
                decisions.append(decision)
        
        return decisions
    
    def _aggregate_decisions(self, raw_decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate and deduplicate similar decisions."""
        if not raw_decisions:
            return []
        
        # Simple deduplication based on similarity
        aggregated = []
        seen_decisions = set()
        
        for decision in raw_decisions:
            decision_key = decision.get("decision", "").lower()[:50]
            if decision_key not in seen_decisions:
                seen_decisions.add(decision_key)
                aggregated.append(decision)
        
        return aggregated
    
    def _enhance_decision_structure(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance decisions with better structure and categorization."""
        enhanced_decisions = []
        
        for decision in decisions:
            # Enhance the decision structure
            enhanced = {
                "text": decision.get("decision", ""),  # Frontend compatibility
                "title": decision.get("title", ""),
                "category": decision.get("category", "other"),
                "participants": decision.get("participants", []),
                "supporting_statements": decision.get("supporting_statements", []),
                "quantitative_data": decision.get("quantitative_data", {}),
                "confidence": decision.get("confidence", 0.5),
                "decision_type": decision.get("decision_type", "explicit"),
                "speaker": decision.get("participants", [None])[0],  # Frontend compatibility
                "timestamp": None  # Frontend compatibility
            }
            enhanced_decisions.append(enhanced)
        
        return enhanced_decisions
    
    def _build_extraction_context(self, segments: List[TranscriptSegment]) -> str:
        """Build formatted context for extraction."""
        context_lines = []
        for seg in segments:
            speaker_part = f"{seg.speaker}: " if seg.speaker else ""
            timestamp_part = f"[{seg.timestamp}] " if seg.timestamp else ""
            context_lines.append(f"{timestamp_part}{speaker_part}{seg.text}")
        
        return "\n".join(context_lines)
    
    def _generate_decision_title(self, text: str) -> str:
        """Generate a concise title for the decision."""
        text_lower = text.lower()
        
        # Pattern-based title generation
        if "launch" in text_lower and ("date" in text_lower or "timeline" in text_lower):
            return "Launch Date Change"
        elif "feature" in text_lower and ("cut" in text_lower or "remove" in text_lower):
            return "Feature Set Reduction"
        elif "budget" in text_lower or "cost" in text_lower or "$" in text:
            return "Budget Allocation"
        elif "security" in text_lower or "audit" in text_lower:
            return "Security Audit Decision"
        elif "meeting" in text_lower or "checkpoint" in text_lower:
            return "Communication Process"
        else:
            # Extract first few words as title
            words = text.split()[:4]
            return " ".join(words) + ("..." if len(words) == 4 else "")
    
    def _categorize_decision(self, text: str) -> str:
        """Categorize decision based on content."""
        text_lower = text.lower()
        
        category_keywords = {
            "timeline": ["date", "deadline", "schedule", "delay", "postpone", "timeline"],
            "features": ["feature", "scope", "functionality", "requirement", "cut", "add"],
            "budget": ["budget", "cost", "money", "allocation", "$", "funding"],
            "security": ["security", "audit", "compliance", "risk"],
            "communication": ["meeting", "checkpoint", "report", "update", "standup"],
            "resources": ["team", "assign", "resource", "staff", "hire"],
            "process": ["process", "workflow", "procedure", "methodology"]
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "other"
    
    def _extract_quantitative_data(self, text: str) -> Dict[str, List[str]]:
        """Extract quantitative data from decision text."""
        dates = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?\b', text)
        dates.extend(re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text))
        
        numbers = re.findall(r'\b\d+\b', text)
        
        # Extract before/after comparisons
        changes = []
        if " from " in text.lower() and " to " in text.lower():
            change_match = re.search(r'from ([^to]+) to ([^,.\n]+)', text, re.IGNORECASE)
            if change_match:
                changes.append(f"{change_match.group(1).strip()} → {change_match.group(2).strip()}")
        
        return {
            "dates": dates,
            "numbers": numbers,
            "changes": changes
        }