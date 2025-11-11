"""Specialized extractors for decisions, actions, and risks with intent tagging."""
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
                    # Get embedding for sentence
                    sentence_embedding = self.embedding_model.encode([sentence])[0]
                    
                    # Calculate similarity to each intent
                    intent_scores = {}
                    for intent, intent_embedding in self._intent_embeddings.items():
                        similarity = cosine_similarity(
                            [sentence_embedding],
                            [intent_embedding]
                        )[0][0]
                        intent_scores[intent] = similarity
                    
                    # Get top intents (similarity > 0.5)
                    top_intents = [
                        intent for intent, score in intent_scores.items()
                        if score > 0.5
                    ]
                    top_intents.sort(key=lambda x: intent_scores[x], reverse=True)
                    
                    # Calculate confidence (max similarity)
                    confidence = max(intent_scores.values()) if intent_scores else 0.5
                    
                    # If no strong intent, default to "discussion"
                    if not top_intents:
                        top_intents = ["discussion"]
                        confidence = 0.4
                    
                    tags.append(IntentTag(
                        sentence=sentence,
                        speaker=seg.speaker,
                        timestamp=seg.timestamp,
                        intent=top_intents[:2],  # Top 2 intents
                        confidence=confidence
                    ))
                except Exception as e:
                    # Fallback to keyword-based for this sentence
                    keyword_intent = self._tag_sentence_with_keywords(sentence)
                    tags.append(IntentTag(
                        sentence=sentence,
                        speaker=seg.speaker,
                        timestamp=seg.timestamp,
                        intent=[keyword_intent] if keyword_intent else ["discussion"],
                        confidence=0.5
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
    """Specialized extractor for key decisions."""
    
    DECISION_PROMPT = """Extract key decisions made in this meeting. 
A decision is a statement where participants agreed, finalized, approved, or settled on something.

Focus on:
- Explicit agreements ("we decided", "we agreed", "approved")
- Finalized plans or approaches
- Resolved disputes or choices

Return JSON format:
{
  "decisions": [
    {
      "decision": "short decision text",
      "rationale": "why this decision was made (if mentioned)",
      "participants": ["speaker names involved"],
      "confidence": 0.0-1.0
    }
  ]
}

Text to analyze:
{text}

Return ONLY valid JSON. Do not include explanatory text."""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize decision extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract decisions from tagged sentences."""
        # Filter for decision intents - lower threshold to catch more decisions
        decision_sentences = [
            tag for tag in tagged_sentences
            if "decision" in tag.intent and tag.confidence > 0.5
        ]
        
        # Also check for explicit decision keywords even if intent tagging missed them
        if not decision_sentences or len(decision_sentences) < 3:
            # Look for explicit decision patterns in all segments
            decision_keywords = ['decided', 'decision', 'agreed', 'approved', 'concluded', 
                               'finalized', 'settled', 'voted', 'unanimously', 'let\'s make a decision']
            for seg in all_segments:
                text_lower = seg.text.lower()
                if any(kw in text_lower for kw in decision_keywords):
                    # Check if this segment is already tagged
                    if not any(tag.sentence in seg.text for tag in decision_sentences):
                        # Create a new intent tag for this decision
                        from app.extraction.specialized_extractors import IntentTag
                        decision_tag = IntentTag(
                            sentence=seg.text,
                            speaker=seg.speaker,
                            timestamp=seg.timestamp,
                            intent=["decision"],
                            confidence=0.7
                        )
                        decision_sentences.append(decision_tag)
        
        if not decision_sentences:
            return []
        
        decisions = []
        seen_decisions = set()
        
        for tag in decision_sentences:
            # Skip if too similar to already extracted decision
            if self._is_duplicate(tag.sentence, seen_decisions):
                continue
            
            # Extract decision details
            decision = self._extract_decision_details(tag, all_segments)
            
            if decision and decision.get("decision"):
                decisions.append(decision)
                seen_decisions.add(tag.sentence.lower()[:50])  # Track for deduplication
        
        # Deduplicate and merge similar decisions
        decisions = self._deduplicate_decisions(decisions)
        
        return decisions
    
    def _extract_decision_details(self, tag: IntentTag, all_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract detailed decision information."""
        sentence = tag.sentence
        sentence_lower = sentence.lower()
        
        # Get context for better extraction
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        
        # Build decision text from context - look at surrounding segments for full decision
        decision_text = sentence
        if tag_idx is not None:
            # Look at next few segments for continuation of decision
            context_parts = [sentence]
            for offset in [1, 2, 3]:
                idx = tag_idx + offset
                if 0 <= idx < len(all_segments):
                    seg = all_segments[idx]
                    # Check if this segment continues the decision (same speaker or related topic)
                    if seg.speaker == tag.speaker or any(kw in seg.text.lower() for kw in ['decided', 'agreed', 'approved', 'concluded', 'finalized']):
                        context_parts.append(seg.text)
                    else:
                        break
            decision_text = ' '.join(context_parts)
        
        # Extract participants (look for "we", team names, or speaker)
        participants = []
        if tag.speaker:
            participants.append(tag.speaker)
        
        # Look for "we", "team", "the group" etc.
        if re.search(r'\b(we|team|the group|everyone|unanimously)\b', sentence_lower):
            # Find other speakers in nearby segments
            if tag_idx is not None:
                # Look at segments before and after
                for offset in [-3, -2, -1, 1, 2, 3]:
                    idx = tag_idx + offset
                    if 0 <= idx < len(all_segments):
                        seg = all_segments[idx]
                        if seg.speaker and seg.speaker not in participants:
                            participants.append(seg.speaker)
        
        # Extract rationale (look for "because", "since", "due to")
        rationale = None
        rationale_patterns = [
            r'because\s+(.+?)(?:\.|$)',
            r'since\s+(.+?)(?:\.|$)',
            r'due to\s+(.+?)(?:\.|$)',
            r'given\s+that\s+(.+?)(?:\.|$)',
            r'to\s+(?:provide|ensure|allow|give)\s+(.+?)(?:\.|$)',
        ]
        
        for pattern in rationale_patterns:
            match = re.search(pattern, decision_text, re.IGNORECASE)
            if match:
                rationale = match.group(1).strip()
                break
        
        # Try to extract a decision title/topic
        decision_title = None
        # Look for patterns like "Launch Date Change", "Final Feature Set", etc.
        title_patterns = [
            r'(?:decision|decided|agreed)\s+(?:on|to|that)\s+(?:the\s+)?([A-Z][^.]{5,50}?)(?:\.|$)',
            r'([A-Z][^.]{5,50}?):\s+(?:we|the team|everyone)\s+(?:decided|agreed|approved)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, decision_text, re.IGNORECASE)
            if match:
                decision_title = match.group(1).strip()
                if len(decision_title) > 50:
                    decision_title = decision_title[:50] + "..."
                break
        
        # Calculate confidence
        confidence = tag.confidence
        
        # Boost confidence for explicit decision words
        explicit_words = ['decided', 'agreed', 'approved', 'finalized', 'settled', 'concluded', 'unanimously']
        if any(word in sentence_lower for word in explicit_words):
            confidence = min(confidence + 0.15, 1.0)
        
        # Boost if we found participants
        if len(participants) > 1:
            confidence = min(confidence + 0.05, 1.0)
        
        return {
            "text": decision_text,
            "title": decision_title,
            "rationale": rationale,
            "speaker": tag.speaker,
            "participants": list(set(participants)) if participants else ["Unclear"],
            "timestamp": tag.timestamp,
            "confidence": round(confidence, 2)
        }
    
    def _is_duplicate(self, sentence: str, seen: set) -> bool:
        """Check if sentence is duplicate of seen decisions."""
        key = sentence.lower()[:50].strip()
        return key in seen
    
    def _deduplicate_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and merge similar decisions."""
        if not self.embedding_model or len(decisions) <= 1:
            return decisions
        
        try:
            # Group by similarity
            unique_decisions = []
            used_indices = set()
            
            for i, decision in enumerate(decisions):
                if i in used_indices:
                    continue
                
                # Find similar decisions
                similar = [decision]
                decision_text = decision["decision"]
                decision_embedding = self.embedding_model.encode([decision_text])[0]
                
                for j, other in enumerate(decisions[i+1:], start=i+1):
                    if j in used_indices:
                        continue
                    
                    other_text = other["decision"]
                    other_embedding = self.embedding_model.encode([other_text])[0]
                    
                    similarity = cosine_similarity(
                        [decision_embedding],
                        [other_embedding]
                    )[0][0]
                    
                    if similarity > 0.8:  # High similarity = duplicate
                        similar.append(other)
                        used_indices.add(j)
                
                # Merge similar decisions
                if len(similar) > 1:
                    # Use the most confident one
                    merged = max(similar, key=lambda x: x.get("confidence", 0))
                    # Combine participants
                    all_participants = []
                    for s in similar:
                        all_participants.extend(s.get("participants", []))
                    merged["participants"] = list(set(all_participants))
                    unique_decisions.append(merged)
                else:
                    unique_decisions.append(decision)
                
                used_indices.add(i)
            
            return unique_decisions
        except:
            # Fallback: simple deduplication by text
            seen = set()
            unique = []
            for decision in decisions:
                key = decision["decision"].lower()[:50]
                if key not in seen:
                    seen.add(key)
                    unique.append(decision)
            return unique


class ActionExtractor:
    """Specialized extractor for action items."""
    
    ACTION_PROMPT = """Extract all action items from this meeting transcript.

An action item is a task or commitment with:
- An owner (person responsible)
- A clear action to be taken
- Optionally a due date or timeline

Return JSON format:
{
  "action_items": [
    {
      "action": "what needs to be done",
      "owner": "person name or 'Unclear'",
      "due_date": "date or null",
      "priority": "high|medium|low",
      "confidence": 0.0-1.0
    }
  ]
}

Text to analyze:
{text}

Return ONLY valid JSON. Do not include explanatory text."""

    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize action extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract action items from tagged sentences."""
        # Filter for action intents - lower threshold to catch more actions
        action_sentences = [
            tag for tag in tagged_sentences
            if "action" in tag.intent and tag.confidence > 0.5
        ]
        
        # Also check for explicit action keywords even if intent tagging missed them
        if not action_sentences or len(action_sentences) < 5:
            # Look for explicit action patterns in all segments
            action_keywords = ['will', 'can you', 'I will', 'assigned', 'responsible', 
                             'handle', 'take care of', 'follow up', 'I\'ll', 'we need to']
            for seg in all_segments:
                text_lower = seg.text.lower()
                if any(kw in text_lower for kw in action_keywords):
                    # Check if this segment is already tagged
                    if not any(tag.sentence in seg.text for tag in action_sentences):
                        # Create a new intent tag for this action
                        from app.extraction.specialized_extractors import IntentTag
                        action_tag = IntentTag(
                            sentence=seg.text,
                            speaker=seg.speaker,
                            timestamp=seg.timestamp,
                            intent=["action"],
                            confidence=0.65
                        )
                        action_sentences.append(action_tag)
        
        if not action_sentences:
            return []
        
        action_items = []
        seen_actions = set()
        
        for tag in action_sentences:
            # Skip duplicates
            if self._is_duplicate(tag.sentence, seen_actions):
                continue
            
            # Check if sentence contains multiple actions (e.g., "do X and Y" or "do X, Y, and Z")
            multiple_actions = self._split_compound_actions(tag.sentence, tag, all_segments)
            
            if multiple_actions:
                # Extract each action separately
                for action_text, owner in multiple_actions:
                    action_item = self._extract_action_details_from_text(action_text, owner, tag, all_segments)
                    if action_item and action_item.get("action"):
                        action_items.append(action_item)
                        seen_actions.add(action_text.lower()[:50])
            else:
                # Single action
                action_item = self._extract_action_details(tag, all_segments)
                if action_item and action_item.get("action"):
                    action_items.append(action_item)
                    seen_actions.add(tag.sentence.lower()[:50])
        
        # Merge related actions by same owner
        action_items = self._merge_related_actions(action_items)
        
        return action_items
    
    def _split_compound_actions(self, sentence: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> List[Tuple[str, str]]:
        """Split compound actions like 'do X and Y' into separate actions."""
        actions = []
        sentence_lower = sentence.lower()
        
        # Pattern 1: "I need to do X, and Y, and Z"
        # Pattern 2: "I need to do X and Y"
        # Pattern 3: "do X, Y, and Z"
        
        # Look for "and" or "also" patterns that indicate multiple actions
        if ' and ' in sentence_lower or ', and ' in sentence_lower:
            # Try to split on "and" or comma+and patterns
            # But be careful - "and" can be part of a single action
            parts = re.split(r'\s+and\s+', sentence, re.IGNORECASE)
            if len(parts) > 1:
                # Check if these are actually separate actions
                # Look for action verbs in each part
                action_verbs = ['update', 'coordinate', 'contact', 'send', 'finalize', 'schedule', 'escalate', 'get', 'create']
                for i, part in enumerate(parts):
                    part_lower = part.strip().lower()
                    # Check if this part starts with an action verb or contains one
                    if any(verb in part_lower for verb in action_verbs):
                        # Extract owner
                        owner = self._extract_owner_from_text(part, tag, all_segments)
                        actions.append((part.strip(), owner))
                
                # If we found multiple actions, return them
                if len(actions) > 1:
                    return actions
        
        # Pattern 2: "Also, do X" or "Also do X"
        if sentence_lower.startswith('also') or ', also' in sentence_lower:
            # This might be a continuation of a previous action
            # But we'll treat it as a separate action
            owner = self._extract_owner_from_text(sentence, tag, all_segments)
            # Remove "also" prefix
            clean_sentence = re.sub(r'^(?:also|and)\s*[,]?\s*', '', sentence, flags=re.IGNORECASE)
            if clean_sentence != sentence:
                actions.append((clean_sentence.strip(), owner))
                return actions
        
        return []  # No compound actions found
    
    def _extract_owner_from_text(self, text: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> str:
        """Quick owner extraction from text."""
        # Use speaker if it's "I" pattern
        if re.search(r'\bI\b\s+(?:need|will|have)', text, re.IGNORECASE):
            return tag.speaker or "Unclear"
        
        # Look for person name at start
        name_match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
        if name_match:
            return name_match.group(1)
        
        return tag.speaker or "Unclear"
    
    def _extract_action_details_from_text(self, action_text: str, owner: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract action details from action text string."""
        context_text = self._get_context_around_tag(tag, all_segments, window=5)
        full_text = f"{context_text}\n{action_text}"
        
        # Extract action with details
        action = self._extract_action_text_with_details(action_text, owner, context_text, full_text)
        
        # Extract due date
        due_date = self._extract_due_date(full_text)
        
        # Determine priority
        priority = self._determine_priority(full_text)
        
        # Calculate confidence
        confidence = 0.7  # Base confidence for extracted actions
        
        if owner and owner != "Unclear":
            confidence = min(confidence + 0.1, 1.0)
        if due_date:
            confidence = min(confidence + 0.05, 1.0)
        
        return {
            "action": action,
            "owner": owner,
            "due_date": due_date,
            "priority": priority,
            "confidence": round(confidence, 2)
        }
    
    def _extract_action_details(self, tag: IntentTag, all_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract detailed action item information."""
        sentence = tag.sentence
        sentence_lower = sentence.lower()
        
        # Get context for better extraction - use larger window for actions
        context_text = self._get_context_around_tag(tag, all_segments, window=5)
        full_text = f"{context_text}\n{sentence}"
        
        # Extract owner using NER and patterns with context
        owner = self._extract_owner(sentence, tag, all_segments)
        
        # Extract action text with full context to capture details
        action = self._extract_action_text_with_details(sentence, owner, context_text, full_text)
        
        # Extract due date from context (not just sentence)
        due_date = self._extract_due_date(full_text)
        
        # Determine priority from context
        priority = self._determine_priority(full_text)
        
        # Calculate confidence
        confidence = tag.confidence
        
        # Boost confidence for explicit action words
        explicit_words = ['will', 'assigned', 'responsible', 'handle', 'complete', 'review', 'take action', 'follow up', 'I\'ll', 'need to']
        if any(word in sentence_lower for word in explicit_words):
            confidence = min(confidence + 0.1, 1.0)
        
        # Lower confidence if owner is unclear and no explicit assignment
        if owner == "Unclear" and not re.search(r'\b(?:assigned|responsible|owner|handle|take care|can you|I need you)\b', context_text, re.IGNORECASE):
            confidence = max(confidence - 0.15, 0.3)
        elif owner != "Unclear":
            confidence = min(confidence + 0.05, 1.0)
        
        # Boost confidence if due date is found
        if due_date:
            confidence = min(confidence + 0.05, 1.0)
        
        # Boost confidence if action has details (indicates it's well-formed)
        if len(action) > 50 and ('(' in action or 'for' in action.lower() or 'by' in action.lower()):
            confidence = min(confidence + 0.05, 1.0)
        
        return {
            "action": action,
            "owner": owner,
            "due_date": due_date,
            "priority": priority,
            "confidence": round(confidence, 2)
        }
    
    def _extract_action_text_with_details(self, sentence: str, owner: str, context_text: str, full_text: str) -> str:
        """Extract action text with full details like names in parentheses, purposes, etc."""
        # Pattern 1: "Person, can you do X (details) by Y for Z"
        # Extract full action with all details
        action_patterns = [
            # "Person, can you do X (with details) for Y"
            rf'(?:{re.escape(owner) if owner != "Unclear" else r"\w+"}[,\s]+)?(?:can you|I\'d like you to|I want you to|I need you to)\s+(.+?)(?:\.|$)',
            # "Person will do X (details) by Y"
            rf'(?:{re.escape(owner) if owner != "Unclear" else r"\w+"}[,\s]+)?(?:will|need to|should|must)\s+(.+?)(?:\.|$)',
            # "I need to do X (details) by Y"
            r'\bI\b\s+(?:need to|will|have to|must)\s+(.+?)(?:\.|$)',
        ]
        
        action = None
        for pattern in action_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                action = match.group(1).strip()
                break
        
        if not action:
            # Fallback: use sentence and clean it
            action = sentence
            if owner and owner != "Unclear":
                action = re.sub(rf'^{re.escape(owner)}[,\s]+', '', action, flags=re.IGNORECASE)
        
        # Look for additional details in context that should be included
        # Extract "for X" purpose from the assignment context
        # Pattern: "Person, can you do X for Y"
        purpose_match = re.search(rf'(?:can you|I\'d like you to|I want you to|I need you to)\s+.+?\s+(?:for|to)\s+([^.]{{10,80}}?)(?:\.|$)', full_text, re.IGNORECASE)
        if purpose_match:
            purpose = purpose_match.group(1).strip()
            if purpose and purpose not in action.lower():
                # Check if purpose is already implied
                if 'for ' not in action.lower():
                    action += " for " + purpose
        
        # Look for specific names/entities mentioned in context
        # Pattern: "Mike Hendricks" or other proper nouns in context
        # Look for names mentioned in nearby segments that relate to the action
        context_sentences = full_text.split('.')
        for ctx_sent in context_sentences:
            # Look for patterns like "account manager, Mike Hendricks" or "Mike Hendricks" near account manager
            if 'account manager' in ctx_sent.lower() or 'contact' in ctx_sent.lower() or 'email' in ctx_sent.lower():
                # Pattern: "Name" or "Name, title" or "title Name"
                name_patterns = [
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "Mike Hendricks"
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s+',  # "Mike Hendricks,"
                ]
                for pattern in name_patterns:
                    matches = re.findall(pattern, ctx_sent)
                    for match in matches:
                        # Check if it looks like a name (2 words, capitalized)
                        if len(match.split()) == 2 and match not in action:
                            # Check if this name is already mentioned in a different context
                            if match.lower() not in action.lower():
                                # Add in parentheses
                                if '(' not in action or match not in action:
                                    # Find where to insert - before "by" or at a logical point
                                    if ' by ' in action.lower():
                                        action = action.replace(' by ', f' ({match}) by ', 1)
                                    elif 'account manager' in action.lower():
                                        action = action.replace('account manager', f'account manager ({match})', 1)
                                    else:
                                        # Insert before the last word or at end
                                        words = action.split()
                                        if len(words) > 3:
                                            words.insert(-1, f'({match})')
                                            action = ' '.join(words)
                                        else:
                                            action += f' ({match})'
                                break
        
        # Look for specific details like "by end of day tomorrow" - should be preserved
        # Extract full time expressions
        time_expr_pattern = r'(?:by|due|deadline)\s+(?:end\s+of\s+)?(?:day\s+)?(\w+(?:\s+\w+)?)'
        time_match = re.search(time_expr_pattern, full_text, re.IGNORECASE)
        if time_match and 'by ' not in action.lower():
            time_expr = time_match.group(0).strip()
            if time_expr not in action:
                action += " " + time_expr
        
        return self._clean_action_text(action)
    
    def _extract_owner(self, sentence: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> str:
        """Extract action owner using NER, patterns, and context-aware analysis."""
        # Get context from surrounding segments
        context_text = self._get_context_around_tag(tag, all_segments, window=3)
        full_context = f"{context_text}\n{sentence}"
        
        # Try NER on full context
        try:
            entities = self.model_adapter.extract_entities(full_context)
            if isinstance(entities, list):
                person_entities = []
                for entity in entities:
                    if isinstance(entity, dict):
                        entity_type = entity.get('entity_group', entity.get('label', ''))
                        if entity_type in ['PER', 'PERSON']:
                            person_entities.append(entity.get('word', ''))
                
                # If we found person entities, use them for better matching
                if person_entities:
                    # Check if any person entity appears in assignment patterns
                    for person in person_entities:
                        # Pattern: "Person will do X" or "Person, can you do X"
                        if re.search(rf'\b{re.escape(person)}\b\s+(?:will|can|should|needs? to)', context_text, re.IGNORECASE):
                            return person
                        # Pattern: "assigned to Person" or "Person is responsible"
                        if re.search(rf'(?:assigned to|responsible for|owner is)\s+\b{re.escape(person)}\b', context_text, re.IGNORECASE):
                            return person
        except:
            pass
        
        # Pattern 1: "Person will do X" or "Person, can you do X"
        pattern1 = re.search(r'^(\w+(?:\s+\w+)?)[,\s]+(?:will|can|should|needs? to)\s+', sentence, re.IGNORECASE)
        if pattern1:
            owner_candidate = pattern1.group(1).strip().rstrip(',')
            if self._looks_like_name(owner_candidate):
                return owner_candidate
        
        # Pattern 2: "assigned to Person" or "Person is assigned"
        pattern2 = re.search(r'(?:assigned\s+to|owner is)\s+(\w+(?:\s+\w+)?)', context_text, re.IGNORECASE)
        if pattern2:
            owner_candidate = pattern2.group(1)
            if self._looks_like_name(owner_candidate):
                return owner_candidate
        
        # Pattern 3: "Person is responsible for" or "Person, you're responsible"
        pattern3 = re.search(r'(\w+(?:\s+\w+)?)\s+(?:is|are)\s+responsible', context_text, re.IGNORECASE)
        if pattern3:
            return pattern3.group(1)
        
        # Pattern 4: "Person, can you..." or "Person, I need you to..." or "Person, I'd like you to..."
        pattern4 = re.search(r'(\w+(?:\s+\w+)?)[,\s]+(?:can you|I need you to|I want you to|I\'d like you to)', context_text, re.IGNORECASE)
        if pattern4:
            owner_candidate = pattern4.group(1).strip().rstrip(',')
            if self._looks_like_name(owner_candidate):
                return owner_candidate
        
        # Pattern 5: "Person, do X" or "Person, I want you to do X"
        pattern5 = re.search(r'^(\w+(?:\s+\w+)?)[,\s]+(?:I want you to|I need you to|I\'d like you to)', sentence, re.IGNORECASE)
        if pattern5:
            owner_candidate = pattern5.group(1).strip().rstrip(',')
            if self._looks_like_name(owner_candidate):
                return owner_candidate
        
        # Pattern 6: "I will" or "I need to" -> use speaker
        if re.search(r'\bI\b\s+(?:will|can|should|need to|have to|must)', sentence, re.IGNORECASE):
            return tag.speaker or "Unclear"
        
        # Pattern 7: Look for explicit assignment in previous segments
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        if tag_idx is not None:
            # Check previous segments for explicit assignment
            for offset in [-5, -4, -3, -2, -1]:
                idx = tag_idx + offset
                if 0 <= idx < len(all_segments):
                    seg = all_segments[idx]
                    seg_text = seg.text.lower()
                    # Look for assignment patterns in previous segments
                    if re.search(r'(?:assign|give|give this to|handle|take care of|responsible)', seg_text):
                        # Extract person name from this segment
                        try:
                            seg_entities = self.model_adapter.extract_entities(seg.text)
                            if isinstance(seg_entities, list):
                                for entity in seg_entities:
                                    if isinstance(entity, dict):
                                        entity_type = entity.get('entity_group', entity.get('label', ''))
                                        if entity_type in ['PER', 'PERSON']:
                                            return entity.get('word', '')
                        except:
                            pass
                        # Fallback: use speaker if segment mentions assignment
                        if seg.speaker:
                            return seg.speaker
        
        # Pattern 8: Look for "I'll start" or "I need to" patterns
        if re.search(r'\bI\b\s+(?:need to|will|have to|must)\s+', sentence, re.IGNORECASE):
            return tag.speaker or "Unclear"
        
        # Pattern 9: Use speaker as owner if no other pattern matched
        if tag.speaker:
            return tag.speaker
        
        return "Unclear"
    
    def _get_context_around_tag(self, tag: IntentTag, all_segments: List[TranscriptSegment], window: int = 3) -> str:
        """Get surrounding context text for better extraction."""
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        if tag_idx is None:
            return ""
        
        context_segments = []
        start_idx = max(0, tag_idx - window)
        end_idx = min(len(all_segments), tag_idx + window + 1)
        
        for idx in range(start_idx, end_idx):
            context_segments.append(all_segments[idx].text)
        
        return " ".join(context_segments)
    
    def _extract_action_text(self, sentence: str, owner: str, context_text: str = "") -> str:
        """Extract the action text from sentence with full context."""
        # Use context if available for better extraction
        full_text = f"{context_text} {sentence}" if context_text else sentence
        full_text_lower = full_text.lower()
        
        # Pattern 1: "Person, can you do X" or "Person, I'd like you to do X"
        pattern1 = re.search(rf'(?:{re.escape(owner) if owner != "Unclear" else r"\w+"}[,\s]+)?(?:can you|I\'d like you to|I want you to|I need you to)\s+(.+?)(?:\.|$)', full_text, re.IGNORECASE)
        if pattern1:
            action = pattern1.group(1).strip()
            # Include additional context if it's a continuation
            if len(action) < 50 and context_text:
                # Look for "for X" or "to X" patterns after the action
                context_match = re.search(rf'{re.escape(action)}\s+(?:for|to)\s+(.+?)(?:\.|$)', full_text, re.IGNORECASE)
                if context_match:
                    action += " " + context_match.group(1).strip()
            return self._clean_action_text(action)
        
        # Pattern 2: "Person will do X" - extract full action with purpose
        pattern2 = re.search(rf'(?:{re.escape(owner) if owner != "Unclear" else r"\w+"}[,\s]+)?(?:will|need to|should|must)\s+(.+?)(?:\.|$)', full_text, re.IGNORECASE)
        if pattern2:
            action = pattern2.group(1).strip()
            # Look for purpose/context in surrounding text
            if context_text:
                # Check for "for X" or "to X" patterns
                purpose_match = re.search(rf'(?:for|to)\s+([^.]{{10,100}}?)(?:\.|$)', context_text, re.IGNORECASE)
                if purpose_match and purpose_match.group(1) not in action.lower():
                    action += " for " + purpose_match.group(1).strip()
            return self._clean_action_text(action)
        
        # Pattern 3: "I need to do X" or "I'll do X"
        pattern3 = re.search(r'\bI\b\s+(?:need to|will|can|should|must|have to)\s+(.+?)(?:\.|$)', sentence, re.IGNORECASE)
        if pattern3:
            action = pattern3.group(1).strip()
            return self._clean_action_text(action)
        
        # Pattern 4: Just remove owner and filler words
        action = sentence
        if owner and owner != "Unclear":
            # Remove owner name at start
            action = re.sub(rf'^{re.escape(owner)}[,\s]+', '', action, flags=re.IGNORECASE)
        
        # Remove common action prefixes
        action = re.sub(r'^(?:can you|I need you to|I want you to|I\'d like you to)\s+', '', action, flags=re.IGNORECASE)
        action = re.sub(r'^(?:so|okay|alright|well|now|then|also|and)\s+', '', action, flags=re.IGNORECASE)
        
        # Clean up
        action = action.strip()
        if not action or len(action) < 10:
            return sentence  # Fallback to original if too short
        
        return self._clean_action_text(action)
    
    def _clean_action_text(self, action: str) -> str:
        """Clean and format action text."""
        # Remove trailing filler words
        action = re.sub(r'\s+(?:so|okay|alright|well|now|then|also|and)$', '', action, flags=re.IGNORECASE)
        
        # Capitalize first letter
        if action:
            action = action[0].upper() + action[1:] if len(action) > 1 else action.upper()
        
        # Ensure it ends with proper punctuation if it's a complete sentence
        if not action.endswith(('.', '!', '?')):
            # If it's a complete sentence, add period
            if len(action.split()) > 5:
                action += '.'
        
        return action.strip()
    
    def _extract_due_date(self, sentence: str) -> Optional[str]:
        """Extract due date from sentence."""
        date_patterns = [
            r'by\s+(?:end\s+of\s+)?(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\w+)?)',
            r'by\s+(?:end\s+of\s+)?(\w+day)',
            r'by\s+(?:end\s+of\s+)?(\w+)',  # "by tomorrow", "by Thursday", "by end of week"
            r'due\s+(?:by\s+)?(.+?)(?:\.|$)',
            r'(\w+day)',  # "tomorrow", "Friday", etc.
            r'next\s+(\w+day)',  # "next Tuesday"
            r'next\s+week',
            r'end\s+of\s+(\w+)',  # "end of week", "end of month"
            r'(\d{1,2}/\d{1,2})',  # "10/15"
            r'(\w+\s+\d{1,2})',  # "October 29th"
            r'this\s+(\w+)',  # "this week"
            r'today',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                date_str = match.group(1) if match.groups() else match.group(0)
                # Clean up common patterns
                date_str = date_str.strip()
                # Normalize "end of day tomorrow" -> "end of day tomorrow"
                if 'end of day' in sentence.lower() and 'tomorrow' in sentence.lower():
                    return "end of day tomorrow"
                return date_str
        
        return None
    
    def _determine_priority(self, sentence: str) -> str:
        """Determine action priority."""
        sentence_lower = sentence.lower()
        
        high_keywords = ['urgent', 'critical', 'important', 'asap', 'immediately', 'priority']
        low_keywords = ['low priority', 'when possible', 'nice to have', 'eventually']
        
        if any(kw in sentence_lower for kw in high_keywords):
            return "high"
        elif any(kw in sentence_lower for kw in low_keywords):
            return "low"
        else:
            return "medium"
    
    def _looks_like_name(self, text: str) -> bool:
        """Heuristic to check if text looks like a person name."""
        words = text.split()
        if len(words) < 1 or len(words) > 3:
            return False
        if words[0][0].isupper() and len(words[0]) > 1:
            return True
        return False
    
    def _is_duplicate(self, sentence: str, seen: set) -> bool:
        """Check if sentence is duplicate."""
        key = sentence.lower()[:50].strip()
        return key in seen
    
    def _merge_related_actions(self, action_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge actions by the same owner."""
        if not self.embedding_model or len(action_items) <= 1:
            return action_items
        
        try:
            # Group by owner
            by_owner = {}
            for action in action_items:
                owner = action.get("owner", "Unclear")
                if owner not in by_owner:
                    by_owner[owner] = []
                by_owner[owner].append(action)
            
            # Merge similar actions for each owner
            merged = []
            for owner, actions in by_owner.items():
                if len(actions) == 1:
                    merged.append(actions[0])
                    continue
                
                # Find similar actions
                used = set()
                for i, action1 in enumerate(actions):
                    if i in used:
                        continue
                    
                    similar = [action1]
                    action1_embedding = self.embedding_model.encode([action1["action"]])[0]
                    
                    for j, action2 in enumerate(actions[i+1:], start=i+1):
                        if j in used:
                            continue
                        
                        action2_embedding = self.embedding_model.encode([action2["action"]])[0]
                        similarity = cosine_similarity(
                            [action1_embedding],
                            [action2_embedding]
                        )[0][0]
                        
                        if similarity > 0.75:  # Similar actions
                            similar.append(action2)
                            used.add(j)
                    
                    # Merge similar actions
                    if len(similar) > 1:
                        # Combine action text
                        combined_action = " and ".join([a["action"] for a in similar])
                        # Use highest priority
                        priorities = {"high": 3, "medium": 2, "low": 1}
                        best_priority = max(similar, key=lambda x: priorities.get(x.get("priority", "medium"), 2))
                        merged.append({
                            "action": combined_action,
                            "owner": owner,
                            "due_date": best_priority.get("due_date"),
                            "priority": best_priority.get("priority", "medium"),
                            "confidence": max(a.get("confidence", 0.5) for a in similar)
                        })
                    else:
                        merged.append(action1)
                    used.add(i)
            
            return merged
        except:
            return action_items


class RiskExtractor:
    """Specialized extractor for risks and blockers."""
    
    RISK_PROMPT = """Identify potential risks, blockers, or concerns discussed in this meeting.

Focus on:
- Project risks (timeline, resources, data issues)
- Technical blockers
- Process challenges
- Concerns about feasibility

Return JSON format:
{
  "risks": [
    {
      "risk": "description of the risk",
      "category": "Timeline|Resource|Data|Process|Technical|Other",
      "mentioned_by": "speaker name",
      "confidence": 0.0-1.0
    }
  ]
}

Text to analyze:
{text}

Return ONLY valid JSON. Do not include explanatory text."""

    RISK_CATEGORIES = {
        "Timeline": ["delay", "late", "deadline", "schedule", "timeline", "on time"],
        "Resource": ["resource", "budget", "staff", "people", "capacity", "manpower"],
        "Data": ["data", "quality", "accuracy", "integrity", "missing", "corrupt"],
        "Process": ["process", "workflow", "procedure", "method", "approach"],
        "Technical": ["technical", "system", "integration", "bug", "error", "failure"],
        "Other": []
    }
    
    def __init__(self, model_adapter: ModelAdapter, embedding_model=None):
        """Initialize risk extractor."""
        self.model_adapter = model_adapter
        self.embedding_model = embedding_model
    
    def extract(self, tagged_sentences: List[IntentTag], all_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Extract risks from tagged sentences."""
        # Filter for risk intents - lower threshold to catch more risks
        risk_sentences = [
            tag for tag in tagged_sentences
            if "risk" in tag.intent and tag.confidence > 0.5
        ]
        
        # Also check for explicit risk keywords even if intent tagging missed them
        if not risk_sentences or len(risk_sentences) < 3:
            # Look for explicit risk patterns in all segments
            risk_keywords = ['risk', 'concern', 'issue', 'problem', 'blocker', 'challenge', 
                           'worry', 'threat', 'danger', 'I\'m worried', 'I\'m concerned']
            for seg in all_segments:
                text_lower = seg.text.lower()
                if any(kw in text_lower for kw in risk_keywords):
                    # Check if this segment is already tagged
                    if not any(tag.sentence in seg.text for tag in risk_sentences):
                        # Create a new intent tag for this risk
                        from app.extraction.specialized_extractors import IntentTag
                        risk_tag = IntentTag(
                            sentence=seg.text,
                            speaker=seg.speaker,
                            timestamp=seg.timestamp,
                            intent=["risk"],
                            confidence=0.65
                        )
                        risk_sentences.append(risk_tag)
        
        if not risk_sentences:
            return []
        
        risks = []
        seen_risks = set()
        
        for tag in risk_sentences:
            # Skip duplicates
            if self._is_duplicate(tag.sentence, seen_risks):
                continue
            
            # Extract risk details with context
            risk = self._extract_risk_details(tag, all_segments)
            
            if risk and risk.get("risk"):
                risks.append(risk)
                seen_risks.add(tag.sentence.lower()[:50])
        
        # Deduplicate risks
        risks = self._deduplicate_risks(risks)
        
        return risks
    
    def _extract_risk_details(self, tag: IntentTag, all_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Extract detailed risk information with priority, impact, and mitigation."""
        sentence = tag.sentence
        sentence_lower = sentence.lower()
        
        # Get context for better extraction
        context_text = self._get_context_around_tag(tag, all_segments, window=8)
        full_text = f"{context_text}\n{sentence}"
        
        # Extract risk title/name (e.g., "Security Audit Delay or Failure")
        risk_title = self._extract_risk_title(sentence, full_text)
        
        # Extract risk description (clean it up)
        risk_description = self._clean_risk_description(sentence)
        if not risk_description or len(risk_description) < 20:
            # Try to get better description from context
            risk_description = self._extract_risk_description_from_context(full_text)
        
        # Categorize risk
        category = self._categorize_risk(full_text)
        
        # Extract mentioned_by
        mentioned_by = tag.speaker or "Unclear"
        
        # Extract priority
        priority = self._extract_risk_priority(full_text)
        
        # Extract impact (if mentioned)
        impact = self._extract_risk_impact(full_text)
        
        # Extract mitigation (multiple strategies if available)
        mitigation = self._extract_risk_mitigation(full_text, all_segments, tag)
        mitigation_list = self._extract_multiple_mitigations(full_text, all_segments, tag)
        
        # Extract owners (can be multiple)
        owners = self._extract_risk_owners(full_text, tag, all_segments)
        
        # Calculate confidence
        confidence = tag.confidence
        
        # Boost confidence for explicit risk words
        explicit_words = ['risk', 'blocker', 'problem', 'issue', 'challenge', 'concern', 'worry', 'threat', 'danger', 'biggest risk', 'critical risk']
        if any(word in sentence_lower for word in explicit_words):
            confidence = min(confidence + 0.15, 1.0)
        
        # Boost confidence if mitigation or impact is found
        if mitigation or mitigation_list:
            confidence = min(confidence + 0.1, 1.0)
        if impact:
            confidence = min(confidence + 0.05, 1.0)
        if risk_title:
            confidence = min(confidence + 0.05, 1.0)
        
        return {
            "risk": risk_description,
            "title": risk_title,
            "category": category,
            "priority": priority,
            "impact": impact,
            "mitigation": mitigation_list if mitigation_list else (mitigation if mitigation else None),
            "owner": owners[0] if owners else None,
            "owners": owners if len(owners) > 1 else None,  # Include if multiple owners
            "mentioned_by": mentioned_by,
            "confidence": round(confidence, 2)
        }
    
    def _extract_risk_title(self, sentence: str, full_text: str) -> Optional[str]:
        """Extract a clear risk title/name."""
        # Pattern 1: "the X risk" or "X issue"
        title_patterns = [
            r'(?:the|a|an)\s+([A-Z][^.]{5,50}?)\s+(?:risk|issue|problem|concern|challenge|blocker)',
            r'([A-Z][^.]{5,50}?)\s+(?:delay|failure|issues?|problems?|concerns?)',
            r'biggest\s+risk\s+(?:I see|is|we have)\s+(?:is\s+)?(?:the\s+)?([^.]{5,50}?)(?:\.|$)',
            r'([A-Z][^.]{5,50}?)\s+(?:not resolved|delay or failure|dependency)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up title
                title = re.sub(r'\s+', ' ', title)
                if 10 <= len(title) <= 80:
                    # Capitalize properly
                    words = title.split()
                    if words:
                        words[0] = words[0][0].upper() + words[0][1:].lower() if len(words[0]) > 1 else words[0].upper()
                    return ' '.join(words)
        
        # Pattern 2: Extract from risk description - create title from key words
        # Look for patterns like "X integration delay" or "Y issues"
        risk_keywords = ['integration', 'audit', 'compliance', 'performance', 'security', 'support', 'budget', 'feature', 'capacity', 'infrastructure']
        for keyword in risk_keywords:
            if keyword in full_text.lower():
                # Try to construct title from context
                # Look for "X delay" or "X issues" patterns
                title_pattern = rf'([A-Z][^.]*?{keyword}[^.]*?)(?:\s+(?:delay|issue|problem|risk|concern))'
                match = re.search(title_pattern, full_text, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    # Add appropriate suffix
                    if 'delay' in full_text.lower() and 'delay' not in title.lower():
                        title += " Delay"
                    elif 'issue' in full_text.lower() or 'problem' in full_text.lower():
                        if 'issue' not in title.lower() and 'problem' not in title.lower():
                            title += " Issues"
                    if 10 <= len(title) <= 80:
                        # Properly capitalize
                        words = title.split()
                        title = ' '.join([w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper() for w in words])
                        return title
        
        return None
    
    def _extract_risk_description_from_context(self, full_text: str) -> str:
        """Extract risk description from full context."""
        # Look for risk description patterns
        desc_patterns = [
            r'(?:risk|issue|problem|concern|challenge)\s+(?:is|that|of)\s+(.+?)(?:\.|$)',
            r'if\s+(.+?)(?:\.|$)',  # "if X happens"
            r'(.+?)\s+could\s+(?:result|lead|cause|affect)',
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if 15 <= len(desc) <= 200:
                    return desc[0].upper() + desc[1:] if len(desc) > 1 else desc.upper()
        
        return ""
    
    def _extract_multiple_mitigations(self, text: str, all_segments: List[TranscriptSegment], tag: IntentTag) -> List[str]:
        """Extract multiple mitigation strategies as a list."""
        mitigations = []
        
        # Pattern 1: "For X: we're doing Y" - extract Y
        for_pattern = re.findall(r'for\s+[^:]+:\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
        if for_pattern:
            mitigations.extend([m.strip() for m in for_pattern if 10 <= len(m.strip()) <= 150])
        
        # Pattern 2: Look for list patterns like "1. X, 2. Y" or "- X, - Y"
        list_pattern = re.findall(r'(?:^|\n)\s*[-•*]\s+(.+?)(?:\n|$)', text, re.IGNORECASE | re.MULTILINE)
        if list_pattern:
            mitigations.extend([m.strip() for m in list_pattern if 10 <= len(m.strip()) <= 150])
        
        # Pattern 3: Look for multiple sentences with "we're" or "we will" patterns
        mitigation_sentences = re.findall(r'we\s+(?:are|will|can|should|need to)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
        if mitigation_sentences:
            mitigations.extend([m.strip() for m in mitigation_sentences if 10 <= len(m.strip()) <= 150])
        
        # Look in next segments for mitigation lists
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        if tag_idx is not None:
            for offset in [1, 2, 3, 4, 5, 6, 7]:
                idx = tag_idx + offset
                if 0 <= idx < len(all_segments):
                    seg = all_segments[idx]
                    seg_text = seg.text.lower()
                    # Check if this segment discusses mitigation
                    if any(kw in seg_text for kw in ['mitigation', 'plan', 'doing', 'will', 'can', 'for', 'we\'re', 'we are']):
                        # Extract mitigation from this segment
                        # Pattern: "For X: Y" or "we're doing Y"
                        for_pattern_seg = re.search(r'for\s+[^:]+:\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                        if for_pattern_seg:
                            mit_text = for_pattern_seg.group(1).strip()
                            if 10 <= len(mit_text) <= 150 and mit_text not in mitigations:
                                mitigations.append(mit_text)
                        else:
                            # Try to extract the action part
                            action_match = re.search(r'we\s+(?:are|will|can)\s+(.+?)(?:\.|$)', seg.text, re.IGNORECASE)
                            if action_match:
                                mit_text = action_match.group(1).strip()
                                if 10 <= len(mit_text) <= 150 and mit_text not in mitigations:
                                    mitigations.append(mit_text)
                            else:
                                # Use the whole segment if it's about mitigation
                                if len(seg.text) <= 150 and seg.text not in mitigations:
                                    mitigations.append(seg.text.strip())
        
        # Remove duplicates and limit
        seen = set()
        unique_mitigations = []
        for mit in mitigations:
            mit_lower = mit.lower()
            if mit_lower not in seen:
                seen.add(mit_lower)
                unique_mitigations.append(mit)
        
        return unique_mitigations[:5] if unique_mitigations else []  # Limit to 5 mitigations
    
    def _extract_risk_owners(self, text: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> List[str]:
        """Extract risk owners (can be multiple)."""
        owners = []
        
        # Look for owner patterns
        owner_patterns = [
            r'(?:owner|responsible|assigned to|handle|take care of)\s+(?:is|are)\s+(\w+(?:\s+\w+)?)',
            r'(\w+(?:\s+\w+)?)\s+(?:is|will be|are)\s+(?:owner|responsible|handling)',
            r'(\w+(?:\s+\w+)?)\s+and\s+(\w+(?:\s+\w+)?)\s+(?:are|will be)\s+(?:owners|responsible)',
        ]
        
        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                for group in match.groups():
                    if group and self._looks_like_name(group.strip()):
                        owner = group.strip()
                        if owner not in owners:
                            owners.append(owner)
        
        # Also look for comma-separated owners
        comma_owners = re.search(r'(?:owner|responsible)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?)', text, re.IGNORECASE)
        if comma_owners:
            owners_text = comma_owners.group(1)
            # Split on "and" or comma
            for owner_part in re.split(r'\s+and\s+|\s*,\s*', owners_text):
                owner_part = owner_part.strip()
                if self._looks_like_name(owner_part) and owner_part not in owners:
                    owners.append(owner_part)
        
        return owners
    
    def _get_context_around_tag(self, tag: IntentTag, all_segments: List[TranscriptSegment], window: int = 5) -> str:
        """Get surrounding context text for better extraction."""
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        if tag_idx is None:
            return ""
        
        context_segments = []
        start_idx = max(0, tag_idx - window)
        end_idx = min(len(all_segments), tag_idx + window + 1)
        
        for idx in range(start_idx, end_idx):
            context_segments.append(all_segments[idx].text)
        
        return " ".join(context_segments)
    
    def _clean_risk_description(self, sentence: str) -> str:
        """Clean up risk description."""
        # Remove filler words at start
        risk = re.sub(r'^(?:so|okay|alright|well|now|then|also|and|i think|i\'m|we\'re|there\'s)\s+', '', sentence, flags=re.IGNORECASE)
        risk = risk.strip()
        
        # Capitalize first letter
        if risk:
            risk = risk[0].upper() + risk[1:] if len(risk) > 1 else risk.upper()
        
        return risk
    
    def _extract_risk_priority(self, text: str) -> str:
        """Extract risk priority from text."""
        text_lower = text.lower()
        
        high_keywords = ['critical', 'high priority', 'urgent', 'catastrophic', 'severe', 'major', 'blocking', 'blocker']
        medium_keywords = ['medium', 'moderate', 'significant', 'important']
        low_keywords = ['low', 'minor', 'small', 'minor issue']
        
        if any(kw in text_lower for kw in high_keywords):
            return "HIGH"
        elif any(kw in text_lower for kw in medium_keywords):
            return "MEDIUM"
        elif any(kw in text_lower for kw in low_keywords):
            return "LOW"
        else:
            # Default based on risk keywords
            if any(kw in text_lower for kw in ['risk', 'blocker', 'problem', 'issue', 'challenge']):
                return "MEDIUM"
            return "MEDIUM"
    
    def _extract_risk_impact(self, text: str) -> Optional[str]:
        """Extract risk impact description."""
        # Look for impact patterns
        impact_patterns = [
            r'impact[:\s]+(.+?)(?:\.|$)',
            r'could\s+(?:result in|lead to|cause|affect)\s+(.+?)(?:\.|$)',
            r'would\s+(?:result in|lead to|cause|affect)\s+(.+?)(?:\.|$)',
            r'may\s+(?:result in|lead to|cause|affect)\s+(.+?)(?:\.|$)',
            r'if\s+(?:this|that|we)\s+(?:happens|occurs|fails)\s*[,\s]+(.+?)(?:\.|$)',
        ]
        
        for pattern in impact_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                impact = match.group(1).strip()
                if len(impact) > 10 and len(impact) < 200:
                    return impact
        
        return None
    
    def _extract_risk_mitigation(self, text: str, all_segments: List[TranscriptSegment], tag: IntentTag) -> Optional[str]:
        """Extract risk mitigation plan (single string for backward compatibility)."""
        mitigations = self._extract_multiple_mitigations(text, all_segments, tag)
        if mitigations:
            return mitigations[0]  # Return first mitigation as string
        
        # Fallback to original pattern matching
        mitigation_patterns = [
            r'mitigation[:\s]+(.+?)(?:\.|$)',
            r'to\s+(?:address|fix|resolve|mitigate|handle)\s+(?:this|that|it)[,\s]+(.+?)(?:\.|$)',
            r'we\s+(?:will|can|should|need to|are)\s+(.+?)(?:\.|$)',
            r'plan\s+(?:is|to)\s+(.+?)(?:\.|$)',
            r'for\s+[^:]+:\s+(.+?)(?:\.|$)',  # "For X: we're doing Y"
        ]
        
        for pattern in mitigation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                mitigation = match.group(1).strip()
                if len(mitigation) > 10 and len(mitigation) < 200:
                    return mitigation
        
        # Look in next segments for mitigation
        tag_idx = next((i for i, seg in enumerate(all_segments) 
                       if tag.sentence in seg.text), None)
        if tag_idx is not None:
            # Check next few segments for mitigation
            for offset in [1, 2, 3, 4, 5]:
                idx = tag_idx + offset
                if 0 <= idx < len(all_segments):
                    seg = all_segments[idx]
                    seg_text = seg.text.lower()
                    if any(kw in seg_text for kw in ['mitigation', 'fix', 'resolve', 'address', 'handle', 'plan', 'doing', 'will']):
                        # Extract mitigation from this segment
                        for pattern in mitigation_patterns:
                            match = re.search(pattern, seg.text, re.IGNORECASE)
                            if match:
                                mitigation = match.group(1).strip()
                                if len(mitigation) > 10 and len(mitigation) < 200:
                                    return mitigation
        
        return None
    
    def _extract_risk_owner(self, text: str, tag: IntentTag, all_segments: List[TranscriptSegment]) -> Optional[str]:
        """Extract risk owner if assigned (backward compatibility)."""
        owners = self._extract_risk_owners(text, tag, all_segments)
        return owners[0] if owners else None
    
    def _looks_like_name(self, text: str) -> bool:
        """Heuristic to check if text looks like a person name."""
        words = text.split()
        if len(words) < 1 or len(words) > 3:
            return False
        if words[0][0].isupper() and len(words[0]) > 1:
            return True
        return False
    
    def _categorize_risk(self, sentence: str) -> str:
        """Categorize risk into predefined categories."""
        sentence_lower = sentence.lower()
        
        category_scores = {}
        for category, keywords in self.RISK_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in sentence_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return "Other"
    
    def _is_duplicate(self, sentence: str, seen: set) -> bool:
        """Check if sentence is duplicate."""
        key = sentence.lower()[:50].strip()
        return key in seen
    
    def _deduplicate_risks(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate similar risks."""
        if not self.embedding_model or len(risks) <= 1:
            return risks
        
        try:
            unique_risks = []
            used_indices = set()
            
            for i, risk in enumerate(risks):
                if i in used_indices:
                    continue
                
                similar = [risk]
                risk_text = risk["risk"]
                risk_embedding = self.embedding_model.encode([risk_text])[0]
                
                for j, other in enumerate(risks[i+1:], start=i+1):
                    if j in used_indices:
                        continue
                    
                    other_text = other["risk"]
                    other_embedding = self.embedding_model.encode([other_text])[0]
                    
                    similarity = cosine_similarity(
                        [risk_embedding],
                        [other_embedding]
                    )[0][0]
                    
                    if similarity > 0.8:
                        similar.append(other)
                        used_indices.add(j)
                
                # Use most confident risk
                merged = max(similar, key=lambda x: x.get("confidence", 0))
                unique_risks.append(merged)
                used_indices.add(i)
            
            return unique_risks
        except:
            # Simple deduplication
            seen = set()
            unique = []
            for risk in risks:
                key = risk["risk"].lower()[:50]
                if key not in seen:
                    seen.add(key)
                    unique.append(risk)
            return unique

