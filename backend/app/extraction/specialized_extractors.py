"""Specialized extractors for decisions, actions, and risks with enhanced prompts and context handling."""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.adapter import ModelAdapter
from app.preprocessing.parser import TranscriptSegment
from app.preprocessing.cleaner import TranscriptCleaner


@dataclass
class IntentTag:
    """Represents an intent tag for a sentence."""
    sentence: str
    speaker: Optional[str]
    timestamp: Optional[str]
    intent: List[str]  # ["decision", "action", "risk", "discussion"]
    confidence: float


class IntentTagger:
    """Tag sentences with semantic intents using embeddings."""
    
    # Canonical intent examples for clustering
    INTENT_EXAMPLES = {
        "decision": [
            "we decided to proceed with the plan",
            "we agreed to move forward",
            "the team approved the proposal",
            "we concluded that we should",
            "it was decided that",
            "we finalized the approach",
            "we settled on"
        ],
        "action": [
            "john will handle the deployment",
            "i will send the report by friday",
            "we need to complete the review",
            "sarah is responsible for the dashboard",
            "the team will follow up next week",
            "i'll take care of the documentation"
        ],
        "risk": [
            "there's a risk of delay",
            "we're concerned about the timeline",
            "this could be a blocker",
            "we have an issue with the data",
            "there's a problem with the integration",
            "we're facing a challenge",
            "this might block us"
        ],
        "discussion": [
            "what do you think about",
            "let's discuss the options",
            "i have a question about",
            "we should consider",
            "what are your thoughts",
            "how about we"
        ]
    }
    
    def __init__(self, embedding_model, cleaner: Optional[TranscriptCleaner] = None):
        """Initialize intent tagger with embedding model."""
        self.embedding_model = embedding_model
        self.cleaner = cleaner
        self._intent_embeddings = None
        self._build_intent_embeddings()
    
    def _build_intent_embeddings(self):
        """Pre-compute embeddings for canonical intent examples."""
        if not self.embedding_model:
            return
        
        try:
            self._intent_embeddings = {}
            for intent, examples in self.INTENT_EXAMPLES.items():
                embeddings = self.embedding_model.encode(examples)
                # Average embedding for the intent
                self._intent_embeddings[intent] = np.mean(embeddings, axis=0)
        except Exception as e:
            print(f"Warning: Could not build intent embeddings: {e}")
            self._intent_embeddings = None
    
    def tag_sentences(self, segments: List[TranscriptSegment]) -> List[IntentTag]:
        """Tag sentences with semantic intents."""
        if not self._intent_embeddings or not self.embedding_model:
            # Fallback to keyword-based tagging
            return self._tag_with_keywords(segments)
        
        tags = []
        
        for seg in segments:
            # Split segment into sentences
            sentences = re.split(r'[.!?]+\s+', seg.text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            for sentence in sentences:
                if len(sentence) < 10:  # Skip very short sentences
                    continue
                
                try:
                    # Compute sentence embedding
                    sentence_embedding = self.embedding_model.encode([sentence])[0]
                    
                    # Compare with intent embeddings
                    intent_scores = {}
                    for intent, intent_embedding in self._intent_embeddings.items():
                        similarity = cosine_similarity(
                            [sentence_embedding],
                            [intent_embedding]
                        )[0][0]
                        intent_scores[intent] = similarity
                    
                    # Get intents with high similarity (> 0.6)
                    tagged_intents = [
                        intent for intent, score in intent_scores.items()
                        if score > 0.6
                    ]
                    
                    # If no high-confidence intent, check keywords
                    if not tagged_intents:
                        keyword_intent = self._tag_sentence_with_keywords(sentence)
                        if keyword_intent:
                            tagged_intents = [keyword_intent]
                    
                    # If still no intent, it's discussion
                    if not tagged_intents:
                        tagged_intents = ["discussion"]
                    
                    # Calculate confidence
                    max_score = max(intent_scores.values()) if intent_scores else 0.5
                    confidence = max_score if tagged_intents != ["discussion"] else 0.4
                    
                    tags.append(IntentTag(
                        sentence=sentence,
                        speaker=seg.speaker,
                        timestamp=seg.timestamp,
                        intent=tagged_intents,
                        confidence=confidence
                    ))
                    
                except Exception:
                    # Fallback for this sentence
                    intent = self._tag_sentence_with_keywords(sentence)
                    tags.append(IntentTag(
                        sentence=sentence,
                        speaker=seg.speaker,
                        timestamp=seg.timestamp,
                        intent=[intent] if intent else ["discussion"],
                        confidence=0.6 if intent else 0.4
                    ))
        
        return tags
    
    def _tag_sentence_with_keywords(self, sentence: str) -> Optional[str]:
        """Fallback keyword-based intent tagging."""
        sentence_lower = sentence.lower()
        
        decision_keywords = ['decided', 'agreed', 'approved', 'concluded', 'finalized', 'settled']
        action_keywords = ['will', 'should', 'need to', 'assigned', 'responsible', 'handle', 'complete']
        risk_keywords = ['risk', 'concern', 'issue', 'problem', 'blocker', 'challenge', 'threat']
        
        if any(kw in sentence_lower for kw in decision_keywords):
            return "decision"
        elif any(kw in sentence_lower for kw in action_keywords):
            return "action"
        elif any(kw in sentence_lower for kw in risk_keywords):
            return "risk"
        
        return None
    
    def _tag_with_keywords(self, segments: List[TranscriptSegment]) -> List[IntentTag]:
        """Fallback keyword-based tagging for all segments."""
        tags = []
        for seg in segments:
            sentences = re.split(r'[.!?]+\s+', seg.text)
            for sentence in sentences:
                if len(sentence) < 10:
                    continue
                intent = self._tag_sentence_with_keywords(sentence)
                tags.append(IntentTag(
                    sentence=sentence,
                    speaker=seg.speaker,
                    timestamp=seg.timestamp,
                    intent=[intent] if intent else ["discussion"],
                    confidence=0.6 if intent else 0.4
                ))
        return tags


class DecisionExtractor:
    """Enhanced decision extractor with better prompts and context handling."""
    
    DECISION_PROMPT = """You are an expert meeting analyst. Extract DECISIONS from this meeting transcript.

A DECISION is when participants:
- Agree on a course of action ("we decided to...")
- Make a choice between options ("we chose...")
- Approve something ("approved the plan...")
- Conclude or finalize something ("we concluded that...")
- Set policy or direction ("we will...")

EXAMPLES of decisions:
✅ "We decided to push the launch date from October 15th to October 29th"
✅ "We agreed to cut the custom branding feature"
✅ "The team approved moving forward with the security audit"
✅ "We concluded that we need 2-week buffers between phases"
✅ "Let's make October 29th our new launch date"
✅ "We're going with the hybrid approach"

❌ NOT decisions (just discussion):
- "What do you think about the timeline?"
- "We should consider the risks"
- "Let me check with legal"
- "I'm wondering if we should..."

Extract ALL clear decisions from this meeting transcript:

{context}

Return decisions in this EXACT JSON format:
{{
  "decisions": [
    {{
      "decision": "exact decision made (what was decided)",
      "rationale": "why this decision was made (if mentioned)",
      "participants": ["names of people involved in decision"],
      "confidence": 0.9
    }}
  ]
}}

Focus on WHAT was decided, not discussions about what might be decided.
Return ONLY valid JSON, no explanations."""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize decision extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions with enhanced context and prompting."""
        
        # Check if this is an Ollama adapter (supports structured prompts)
        if hasattr(self.model_adapter, 'extract_structured_data'):
            return self._extract_with_llm(all_segments)
        else:
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_llm(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions using LLM structured prompts (for Ollama)."""
        context = self._build_extraction_context(all_segments)
        
        try:
            response = self.model_adapter.extract_structured_data(
                self.DECISION_PROMPT.format(context=context)
            )
            return response.get("decisions", [])
        except Exception as e:
            print(f"LLM extraction failed: {e}, falling back to pattern matching")
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_patterns(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions using pattern matching (fallback)."""
        
        # Build full context instead of processing individual sentences
        context = self._build_extraction_context(all_segments)
        
        # For HuggingFace models, we'll process in chunks and extract patterns
        decisions = []
        
        # First, try to find decision patterns in segments
        decision_keywords = ['decided', 'decision', 'agreed', 'approved', 'concluded', 
                           'finalized', 'settled', 'voted', 'unanimously', 'let\'s make', 
                           'we will', 'we\'re going with', 'push the', 'change the', 'move to']
        
        for i, seg in enumerate(all_segments):
            text_lower = seg.text.lower()
            
            # Check if this segment contains decision keywords
            if any(kw in text_lower for kw in decision_keywords):
                # Build context around this decision (previous and next segments)
                context_segments = []
                
                # Include 2 segments before and after for context
                for j in range(max(0, i-2), min(len(all_segments), i+3)):
                    context_segments.append(all_segments[j])
                
                # Extract decision from this context
                decision = self._extract_decision_from_context(seg, context_segments, i)
                if decision:
                    decisions.append(decision)
        
        # Deduplicate decisions (temporarily disabled for better results)
        # decisions = self._deduplicate_decisions(decisions)
        
        return decisions
    
    def _build_extraction_context(self, segments: List[TranscriptSegment], max_tokens: int = 2500) -> str:
        """Build context with speaker attribution and natural flow."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            # Format: "Speaker: text"
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3  # Rough token estimate
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)
    
    def _extract_decision_from_context(self, decision_seg: TranscriptSegment, 
                                     context_segments: List[TranscriptSegment], 
                                     seg_index: int) -> Optional[Dict[str, Any]]:
        """Extract decision details from context segments."""
        
        # Build the decision text - may span multiple segments
        decision_text = decision_seg.text
        
        # Check if next segments continue the decision
        for i in range(1, min(3, len(context_segments) - seg_index)):
            next_seg = context_segments[seg_index + i] if seg_index + i < len(context_segments) else None
            if next_seg and (next_seg.speaker == decision_seg.speaker or 
                           any(kw in next_seg.text.lower() for kw in ['to', 'will', 'with', 'for'])):
                # This segment likely continues the decision
                decision_text += " " + next_seg.text
            else:
                break
        
        # Extract the core decision
        decision_patterns = [
            r'(?:decided|agreed|approved|concluded|finalized|settled)\s+(?:to|that|on)\s+([^.!?]+)',
            r'(?:we|the team|everyone)\s+(?:will|are going to)\s+([^.!?]+)',
            r'(?:let\'s|we\'re)\s+(?:make|go with|push|change|move)\s+([^.!?]+)',
            r'(?:push|change|move)\s+(?:the|our)\s+([^.!?]+)\s+(?:to|from)',
        ]
        
        core_decision = None
        for pattern in decision_patterns:
            match = re.search(pattern, decision_text, re.IGNORECASE)
            if match:
                core_decision = match.group(0).strip()
                break
        
        if not core_decision:
            core_decision = decision_text
        
        # Extract rationale
        rationale = None
        rationale_patterns = [
            r'(?:because|since|due to|given that|to provide|to ensure|to give)\s+([^.!?]+)',
        ]
        for pattern in rationale_patterns:
            match = re.search(pattern, decision_text, re.IGNORECASE)
            if match:
                rationale = match.group(1).strip()
                break
        
        # Extract participants
        participants = []
        if decision_seg.speaker:
            participants.append(decision_seg.speaker)
        
        # Look for group decisions
        if re.search(r'\b(we|team|everyone|unanimously|all)\b', decision_text.lower()):
            # Add other speakers from context
            for seg in context_segments:
                if seg.speaker and seg.speaker not in participants:
                    participants.append(seg.speaker)
            # Limit to reasonable number
            participants = participants[:5]
        
        return {
            "decision": core_decision.strip(),
            "rationale": rationale,
            "participants": participants if participants else ["Meeting participants"],
            "confidence": 0.85
        }
    
    def _is_duplicate(self, sentence: str, seen: set) -> bool:
        """Check if sentence is duplicate of seen decisions."""
        key = sentence.lower()[:50].strip()
        return key in seen
    
    def _deduplicate_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and merge similar decisions - currently disabled for better results."""
        return decisions  # Temporarily disabled to avoid over-filtering


class ActionExtractor:
    """Enhanced action extractor with better owner detection and context."""
    
    ACTION_PROMPT = """You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

An ACTION ITEM is a specific task assigned to someone with:
- WHO: Clear owner/assignee
- WHAT: Specific action to take
- WHEN: Due date/deadline (if mentioned)

EXAMPLES of action items:
✅ "Sarah, can you contact the Salesforce account manager by end of day tomorrow?"
   → Owner: Sarah, Action: contact Salesforce account manager, Due: end of day tomorrow

✅ "Marcus will schedule knowledge transfer sessions with James this week"
   → Owner: Marcus, Action: schedule knowledge transfer sessions with James, Due: this week

✅ "Emily needs to update all marketing materials with the new launch date"
   → Owner: Emily, Action: update all marketing materials with new launch date

✅ "I'll coordinate with finance on the security audit budget"
   → Owner: [current speaker], Action: coordinate with finance on security audit budget

✅ "Let's have David send the calendar invites for weekly meetings"
   → Owner: David, Action: send calendar invites for weekly meetings

OWNERSHIP PATTERNS:
- "John will..." → Owner: John
- "Sarah, can you..." → Owner: Sarah
- "I'll handle..." → Owner: [current speaker]
- "Let's have Marcus..." → Owner: Marcus
- "assigned to Emily" → Owner: Emily
- "Emily - update the..." → Owner: Emily

Extract ALL action items from this meeting transcript:

{context}

Return in this EXACT JSON format:
{{
  "action_items": [
    {{
      "action": "specific task to be done",
      "owner": "person responsible (use actual names from transcript)",
      "due_date": "deadline if mentioned (or null if not specified)",
      "priority": "high/medium/low based on urgency words",
      "confidence": 0.9
    }}
  ]
}}

FOCUS on clear task assignments, not vague discussions.
Return ONLY valid JSON, no explanations."""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize action extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items with enhanced owner detection."""
        
        # Check if this is an Ollama adapter (supports structured prompts)
        if hasattr(self.model_adapter, 'extract_structured_data'):
            return self._extract_with_llm(all_segments)
        else:
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_llm(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items using LLM structured prompts (for Ollama)."""
        context = self._build_extraction_context(all_segments)
        
        try:
            response = self.model_adapter.extract_structured_data(
                self.ACTION_PROMPT.format(context=context)
            )
            return response.get("action_items", [])
        except Exception as e:
            print(f"LLM extraction failed: {e}, falling back to pattern matching")
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_patterns(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items using pattern matching (fallback)."""
        
        action_items = []
        seen_actions = set()
        
        # Action patterns that indicate clear assignments
        action_patterns = [
            (r'([A-Za-z]+),?\s+(?:can you|could you|please|will you)\s+([^.!?]+)', 'direct_request'),
            (r'([A-Za-z]+)\s+(?:will|is going to|needs to|should|must)\s+([^.!?]+)', 'will_pattern'),
            (r"(?:I'll|I will|I'm going to)\s+([^.!?]+)", 'first_person'),
            (r'(?:let\'s have|ask|get)\s+([A-Za-z]+)\s+(?:to\s+)?([^.!?]+)', 'delegation'),
            (r'([A-Za-z]+)\s*[-–]\s*([^.!?]+)', 'dash_pattern'),
            (r'assigned to\s+([A-Za-z]+):\s*([^.!?]+)', 'assigned_pattern'),
        ]
        
        for seg in all_segments:
            text = seg.text
            speaker = seg.speaker or "Unknown"
            
            # Try each action pattern
            for pattern, pattern_type in action_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    owner = None
                    action_text = None
                    
                    if pattern_type == 'direct_request':
                        owner = match.group(1)
                        action_text = match.group(2)
                    elif pattern_type == 'will_pattern':
                        owner = match.group(1)
                        action_text = match.group(2)
                    elif pattern_type == 'first_person':
                        owner = speaker
                        action_text = match.group(1)
                    elif pattern_type == 'delegation':
                        owner = match.group(1)
                        action_text = match.group(2)
                    elif pattern_type == 'dash_pattern':
                        owner = match.group(1)
                        action_text = match.group(2)
                    elif pattern_type == 'assigned_pattern':
                        owner = match.group(1)
                        action_text = match.group(2)
                    
                    if owner and action_text:
                        # Clean up the action text
                        action_text = action_text.strip().rstrip('.,')
                        
                        # Skip if too short or already seen
                        if len(action_text) < 10 or action_text.lower() in seen_actions:
                            continue
                        
                        seen_actions.add(action_text.lower())
                        
                        # Extract due date
                        due_date = self._extract_due_date(text)
                        
                        # Determine priority
                        priority = self._determine_priority(text)
                        
                        action_items.append({
                            "action": action_text,
                            "owner": self._clean_owner_name(owner, speaker),
                            "due_date": due_date,
                            "priority": priority,
                            "confidence": 0.85
                        })
        
        # Remove duplicates (temporarily disabled)
        # action_items = self._deduplicate_actions(action_items)
        
        return action_items
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date from text."""
        date_patterns = [
            (r'by\s+(end of day|EOD)\s+tomorrow', 'end of day tomorrow'),
            (r'by\s+([A-Za-z]+day)', None),  # Monday, Tuesday, etc.
            (r'by\s+(next week|this week|tomorrow|today)', None),
            (r'by\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?)', None),  # July 15th
            (r'(?:within|in)\s+(\d+\s+(?:days?|weeks?))', None),
            (r'(?:deadline|due):\s*([^.!?,]+)', None),
        ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if replacement:
                    return replacement
                else:
                    return match.group(1).strip()
        
        return None
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on keywords."""
        text_lower = text.lower()
        
        high_priority_words = ['urgent', 'critical', 'asap', 'immediately', 'priority', 
                              'important', 'blocker', 'blocking', 'must']
        low_priority_words = ['when possible', 'nice to have', 'optional', 'low priority']
        
        if any(word in text_lower for word in high_priority_words):
            return "high"
        elif any(word in text_lower for word in low_priority_words):
            return "low"
        else:
            return "medium"
    
    def _clean_owner_name(self, owner: str, speaker: str) -> str:
        """Clean and standardize owner names."""
        if not owner:
            return "Unclear"
        
        # Clean up the owner name
        owner = owner.strip()
        
        # Handle pronouns
        if owner.lower() in ['i', "i'll", "i'm"]:
            return speaker
        elif owner.lower() in ['you']:
            return "Unclear"
        
        # Remove common titles
        owner = re.sub(r'^(Dr\.|Mr\.|Ms\.|Mrs\.)\s*', '', owner, flags=re.IGNORECASE)
        
        # Capitalize properly
        owner = owner.title()
        
        return owner
    
    def _build_extraction_context(self, segments: List[TranscriptSegment], max_tokens: int = 2500) -> str:
        """Build context with speaker attribution and natural flow."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            # Format: "Speaker: text"
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3  # Rough token estimate
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)
    
    def _deduplicate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate actions - currently disabled."""
        return actions  # Temporarily disabled


class RiskExtractor:
    """Enhanced risk extractor that identifies actual risks, not transcript excerpts."""
    
    RISK_PROMPT = """You are an expert meeting analyst. Extract RISKS from this meeting transcript.

A RISK is a potential problem, concern, or threat that could impact the project:
- Things that could go wrong
- Blockers or dependencies
- Concerns raised by participants
- Potential failures or delays

EXAMPLES of risks:
✅ "Security audit delay could impact launch timeline"
   → Category: Timeline, Risk: Security audit delay impacting launch

✅ "Key engineer taking paternity leave during launch window"
   → Category: Resource, Risk: Key person dependency during critical period

✅ "Performance issues not resolved before launch"
   → Category: Technical, Risk: Unresolved performance issues

✅ "Budget constraints may require cutting more features"
   → Category: Resource, Risk: Budget overrun forcing feature cuts

✅ "If we can't get Salesforce integration working, enterprise customers won't be happy"
   → Category: Technical, Risk: Salesforce integration affecting enterprise customers

RISK CATEGORIES:
- Timeline: delays, schedule issues, deadline conflicts
- Technical: performance, bugs, integration problems, system issues
- Resource: staffing, budget, capacity, key person dependencies
- Regulatory: compliance, legal issues, audit requirements
- Business: market, customer, competitive, stakeholder concerns

Extract ALL risks from this meeting transcript:

{context}

Return in this EXACT JSON format:
{{
  "risks": [
    {{
      "risk": "clear description of the risk/concern (not a quote)",
      "category": "Timeline/Technical/Resource/Regulatory/Business",
      "mentioned_by": "speaker who raised the concern",
      "confidence": 0.9
    }}
  ]
}}

Focus on POTENTIAL PROBLEMS that could impact the project, not general discussion.
Return ONLY valid JSON, no explanations."""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize risk extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks with proper categorization."""
        
        # Check if this is an Ollama adapter (supports structured prompts)
        if hasattr(self.model_adapter, 'extract_structured_data'):
            return self._extract_with_llm(all_segments)
        else:
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_llm(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks using LLM structured prompts (for Ollama)."""
        context = self._build_extraction_context(all_segments)
        
        try:
            response = self.model_adapter.extract_structured_data(
                self.RISK_PROMPT.format(context=context)
            )
            return response.get("risks", [])
        except Exception as e:
            print(f"LLM extraction failed: {e}, falling back to pattern matching")
            return self._extract_with_patterns(all_segments)
    
    def _extract_with_patterns(self, all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks using pattern matching (fallback)."""
        
        risks = []
        seen_risks = set()
        
        # Risk indicator patterns
        risk_patterns = [
            'risk', 'concern', 'worried', 'issue', 'problem', 'blocker', 'blocking',
            'challenge', 'threat', 'delay', 'might not', 'could fail', 'won\'t have',
            'if we don\'t', 'if we can\'t', 'dependency', 'constraint', 'bottleneck',
            'vulnerability', 'exposure', 'gap', 'shortfall', 'deficit'
        ]
        
        for seg in all_segments:
            text_lower = seg.text.lower()
            speaker = seg.speaker or "Unknown"
            
            # Check if segment contains risk indicators
            if any(pattern in text_lower for pattern in risk_patterns):
                # Extract the risk description
                risk_desc = self._extract_risk_description(seg.text)
                
                if risk_desc and risk_desc.lower() not in seen_risks:
                    seen_risks.add(risk_desc.lower())
                    
                    # Categorize the risk
                    category = self._categorize_risk(risk_desc)
                    
                    risks.append({
                        "risk": risk_desc,
                        "category": category,
                        "mentioned_by": speaker,
                        "confidence": 0.85
                    })
        
        # Remove duplicates (temporarily disabled)
        # risks = self._deduplicate_risks(risks)
        
        return risks
    
    def _extract_risk_description(self, text: str) -> Optional[str]:
        """Extract clear risk description from text."""
        
        # Patterns to extract risk descriptions
        risk_extraction_patterns = [
            r'(?:risk|concern|worried)\s+(?:is\s+)?(?:that\s+)?([^.!?]+)',
            r'(?:issue|problem|blocker)\s+(?:is\s+)?(?:with\s+)?([^.!?]+)',
            r'if\s+(?:we\s+)?(?:don\'t|can\'t)\s+([^,]+),\s*([^.!?]+)',
            r'(?:might|could)\s+(?:not\s+)?([^.!?]+)',
            r'(?:delay|constraint|bottleneck)\s+(?:in|with|on)\s+([^.!?]+)',
        ]
        
        for pattern in risk_extraction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract and clean the risk description
                if match.lastindex and match.lastindex > 1:
                    # For patterns with multiple groups, combine them
                    risk_parts = [match.group(i).strip() for i in range(1, match.lastindex + 1)]
                    risk_desc = ' '.join(risk_parts)
                else:
                    risk_desc = match.group(1).strip()
                
                # Clean up the description
                risk_desc = re.sub(r'^(that|is|with)\s+', '', risk_desc, flags=re.IGNORECASE)
                risk_desc = risk_desc.rstrip('.,')
                
                # Ensure it's substantial
                if len(risk_desc) > 15:
                    return risk_desc
        
        # Fallback: use the whole segment if it's clearly a risk
        if any(word in text.lower() for word in ['risk', 'concern', 'blocker', 'issue']):
            # Clean up the text
            clean_text = re.sub(r'^\s*\w+:\s*', '', text)  # Remove speaker prefix
            clean_text = clean_text.strip().rstrip('.,')
            if len(clean_text) > 20 and len(clean_text) < 200:
                return clean_text
        
        return None
    
    def _categorize_risk(self, risk_desc: str) -> str:
        """Categorize risk based on content."""
        risk_lower = risk_desc.lower()
        
        # Category keywords
        timeline_words = ['delay', 'deadline', 'schedule', 'timeline', 'launch', 'date', 'week', 'month']
        technical_words = ['integration', 'performance', 'bug', 'system', 'api', 'technical', 'data', 'security']
        resource_words = ['budget', 'staff', 'person', 'capacity', 'resource', 'team', 'engineer', 'support']
        regulatory_words = ['compliance', 'legal', 'audit', 'regulation', 'gdpr', 'ccpa', 'privacy']
        business_words = ['customer', 'market', 'competitor', 'stakeholder', 'revenue', 'adoption']
        
        # Check categories
        if any(word in risk_lower for word in timeline_words):
            return "Timeline"
        elif any(word in risk_lower for word in technical_words):
            return "Technical"
        elif any(word in risk_lower for word in resource_words):
            return "Resource"
        elif any(word in risk_lower for word in regulatory_words):
            return "Regulatory"
        elif any(word in risk_lower for word in business_words):
            return "Business"
        else:
            return "Other"
    
    def _build_extraction_context(self, segments: List[TranscriptSegment], max_tokens: int = 2500) -> str:
        """Build context with speaker attribution and natural flow."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            # Format: "Speaker: text"
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3  # Rough token estimate
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)
    
    def _deduplicate_risks(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate risks - currently disabled."""
        return risks  # Temporarily disabled