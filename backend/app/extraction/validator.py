"""Validation system for extracted items to detect hallucinations and errors."""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import difflib
from app.preprocessing.parser import TranscriptSegment

logger = logging.getLogger(__name__)


class ExtractionValidator:
    """Validates extractions against source material and common sense."""
    
    def __init__(self, embedding_model=None):
        """Initialize validator.
        
        Args:
            embedding_model: Model for semantic similarity
        """
        self.embedding_model = embedding_model
        self.known_names = set()
        self.company_names = set()
        self.common_roles = {'manager', 'director', 'engineer', 'analyst', 'lead', 'coordinator'}
    
    def validate_decisions(self, decisions: List[Dict[str, Any]], source_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Validate extracted decisions.
        
        Args:
            decisions: List of extracted decisions
            source_segments: Original transcript segments
            
        Returns:
            Decisions with validation information
        """
        validated_decisions = []
        
        for decision in decisions:
            validation = self._validate_single_item(
                decision.get('decision', decision.get('text', '')),
                source_segments,
                item_type='decision'
            )
            
            # Add validation info
            decision['validation'] = validation
            
            # Check for decision-specific issues
            decision_validation = self._validate_decision_logic(decision, source_segments)
            decision['validation'].update(decision_validation)
            
            validated_decisions.append(decision)
        
        return validated_decisions
    
    def validate_actions(self, actions: List[Dict[str, Any]], source_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Validate extracted action items.
        
        Args:
            actions: List of extracted actions
            source_segments: Original transcript segments
            
        Returns:
            Actions with validation information
        """
        validated_actions = []
        
        for action in actions:
            validation = self._validate_single_item(
                action.get('action', ''),
                source_segments,
                item_type='action'
            )
            
            # Add validation info
            action['validation'] = validation
            
            # Check for action-specific issues
            action_validation = self._validate_action_logic(action, source_segments)
            action['validation'].update(action_validation)
            
            validated_actions.append(action)
        
        return validated_actions
    
    def validate_risks(self, risks: List[Dict[str, Any]], source_segments: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """Validate extracted risks.
        
        Args:
            risks: List of extracted risks
            source_segments: Original transcript segments
            
        Returns:
            Risks with validation information
        """
        validated_risks = []
        
        for risk in risks:
            validation = self._validate_single_item(
                risk.get('risk', ''),
                source_segments,
                item_type='risk'
            )
            
            # Add validation info
            risk['validation'] = validation
            
            validated_risks.append(risk)
        
        return validated_risks
    
    def _validate_single_item(self, item_text: str, source_segments: List[TranscriptSegment], item_type: str) -> Dict[str, Any]:
        """Validate a single extracted item.
        
        Args:
            item_text: Text of extracted item
            source_segments: Original segments
            item_type: Type of item (decision, action, risk)
            
        Returns:
            Validation results
        """
        validation = {
            'is_valid': True,
            'confidence': 0.8,
            'issues': [],
            'source_support': 0.0,
            'word_overlap': 0.0
        }
        
        # Check for hallucination
        hallucination_check = self._check_hallucination(item_text, source_segments)
        validation.update(hallucination_check)
        
        # Check for logical consistency
        logic_check = self._check_logical_consistency(item_text, item_type)
        validation['issues'].extend(logic_check)
        
        # Check for completeness
        completeness_check = self._check_completeness(item_text, item_type)
        validation['issues'].extend(completeness_check)
        
        # Overall validity
        validation['is_valid'] = (
            validation['source_support'] > 0.3 and
            len([issue for issue in validation['issues'] if issue['severity'] == 'high']) == 0
        )
        
        return validation
    
    def _check_hallucination(self, item_text: str, source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Check if item text appears to be hallucinated.
        
        Args:
            item_text: Text to check
            source_segments: Source segments
            
        Returns:
            Hallucination check results
        """
        if not item_text or not source_segments:
            return {'source_support': 0.0, 'word_overlap': 0.0}
        
        item_words = set(item_text.lower().split())
        source_text = ' '.join([seg.text for seg in source_segments]).lower()
        source_words = set(source_text.split())
        
        # Calculate word overlap
        overlap = len(item_words & source_words)
        word_overlap = overlap / len(item_words) if item_words else 0.0
        
        # Check for phrases that appear in source
        source_support = self._calculate_phrase_support(item_text, source_text)
        
        # Use semantic similarity if available
        if self.embedding_model:
            semantic_support = self._calculate_semantic_support(item_text, source_segments)
            source_support = max(source_support, semantic_support)
        
        return {
            'source_support': source_support,
            'word_overlap': word_overlap
        }
    
    def _calculate_phrase_support(self, item_text: str, source_text: str) -> float:
        """Calculate how well item phrases are supported by source."""
        item_text = item_text.lower()
        source_text = source_text.lower()
        
        # Check for exact phrase matches
        phrases = self._extract_key_phrases(item_text)
        supported_phrases = 0
        
        for phrase in phrases:
            if phrase in source_text:
                supported_phrases += 1
        
        return supported_phrases / len(phrases) if phrases else 0.0
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text for matching."""
        # Extract noun phrases and important phrases
        phrases = []
        
        # Simple extraction: sequences of 2-4 words
        words = text.split()
        for i in range(len(words)):
            for length in [2, 3, 4]:
                if i + length <= len(words):
                    phrase = ' '.join(words[i:i+length])
                    # Skip if phrase is mostly stopwords
                    if self._is_meaningful_phrase(phrase):
                        phrases.append(phrase.lower())
        
        return phrases
    
    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """Check if phrase is meaningful (not mostly stopwords)."""
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = phrase.lower().split()
        
        if len(words) < 2:
            return False
        
        meaningful_words = [w for w in words if w not in stopwords]
        return len(meaningful_words) >= len(words) * 0.5
    
    def _calculate_semantic_support(self, item_text: str, source_segments: List[TranscriptSegment]) -> float:
        """Calculate semantic similarity support."""
        try:
            item_embedding = self.embedding_model.encode([item_text])[0]
            
            max_similarity = 0.0
            for segment in source_segments:
                segment_embedding = self.embedding_model.encode([segment.text])[0]
                
                from sklearn.metrics.pairwise import cosine_similarity
                similarity = cosine_similarity([item_embedding], [segment_embedding])[0][0]
                max_similarity = max(max_similarity, similarity)
            
            return float(max_similarity)
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0
    
    def _check_logical_consistency(self, item_text: str, item_type: str) -> List[Dict[str, str]]:
        """Check for logical consistency issues."""
        issues = []
        
        # Check for contradictions
        if self._contains_contradiction(item_text):
            issues.append({
                'type': 'contradiction',
                'severity': 'high',
                'message': 'Text contains contradictory statements'
            })
        
        # Type-specific checks
        if item_type == 'action':
            if not self._has_clear_action_verb(item_text):
                issues.append({
                    'type': 'unclear_action',
                    'severity': 'medium',
                    'message': 'Action lacks clear verb or actionable language'
                })
        
        elif item_type == 'decision':
            if not self._has_decision_language(item_text):
                issues.append({
                    'type': 'unclear_decision',
                    'severity': 'medium',
                    'message': 'Decision lacks decisive language'
                })
        
        return issues
    
    def _contains_contradiction(self, text: str) -> bool:
        """Check if text contains contradictory statements."""
        contradiction_patterns = [
            (r'\byes\b.*\bno\b', r'\bno\b.*\byes\b'),
            (r'\bwill\b.*\bwon\'t\b', r'\bwon\'t\b.*\bwill\b'),
            (r'\bcan\b.*\bcan\'t\b', r'\bcan\'t\b.*\bcan\b'),
            (r'\bagree\b.*\bdisagree\b', r'\bdisagree\b.*\bagree\b'),
        ]
        
        text_lower = text.lower()
        for pattern1, pattern2 in contradiction_patterns:
            if re.search(pattern1, text_lower) or re.search(pattern2, text_lower):
                return True
        
        return False
    
    def _has_clear_action_verb(self, text: str) -> bool:
        """Check if action text has clear action verbs."""
        action_verbs = {
            'send', 'create', 'update', 'review', 'complete', 'finish',
            'schedule', 'organize', 'prepare', 'develop', 'implement',
            'follow', 'contact', 'coordinate', 'analyze', 'test'
        }
        
        words = text.lower().split()
        return any(verb in words for verb in action_verbs)
    
    def _has_decision_language(self, text: str) -> bool:
        """Check if decision text has decisive language."""
        decision_words = {
            'decided', 'decision', 'agreed', 'approved', 'chosen',
            'concluded', 'determined', 'resolved', 'settled', 'finalized'
        }
        
        words = text.lower().split()
        return any(word in words for word in decision_words)
    
    def _check_completeness(self, item_text: str, item_type: str) -> List[Dict[str, str]]:
        """Check if extracted item is complete."""
        issues = []
        
        # Check minimum length
        if len(item_text.split()) < 3:
            issues.append({
                'type': 'too_short',
                'severity': 'medium',
                'message': 'Extracted text is very short and may be incomplete'
            })
        
        # Check for truncation indicators
        if item_text.endswith('...') or item_text.endswith(' and'):
            issues.append({
                'type': 'truncated',
                'severity': 'medium',
                'message': 'Text appears to be truncated'
            })
        
        # Type-specific completeness checks
        if item_type == 'action':
            if 'will' in item_text.lower() and not self._has_owner(item_text):
                issues.append({
                    'type': 'missing_owner',
                    'severity': 'low',
                    'message': 'Action item may be missing clear owner assignment'
                })
        
        return issues
    
    def _has_owner(self, text: str) -> bool:
        """Check if action text has clear owner."""
        # Look for names or pronouns
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b'
        pronoun_pattern = r'\b(I|we|he|she|they)\b'
        
        return bool(re.search(name_pattern, text) or re.search(pronoun_pattern, text, re.IGNORECASE))
    
    def _validate_decision_logic(self, decision: Dict[str, Any], source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Validate decision-specific logic."""
        validation = {}
        
        # Check if participants are mentioned in source
        participants = decision.get('participants', [])
        if participants:
            validation['participant_validation'] = self._validate_participants(participants, source_segments)
        
        # Check for quantitative data validation
        if 'quantitative_data' in decision:
            validation['quantitative_validation'] = self._validate_quantitative_data(
                decision['quantitative_data'], source_segments
            )
        
        return validation
    
    def _validate_action_logic(self, action: Dict[str, Any], source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Validate action-specific logic."""
        validation = {}
        
        # Validate owner exists in meeting
        owner = action.get('owner')
        if owner:
            validation['owner_validation'] = self._validate_owner(owner, source_segments)
        
        # Validate due date format
        due_date = action.get('due_date')
        if due_date:
            validation['date_validation'] = self._validate_date_format(due_date)
        
        return validation
    
    def _validate_participants(self, participants: List[str], source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Validate that participants appear in source."""
        source_text = ' '.join([seg.text for seg in source_segments]).lower()
        source_speakers = set([seg.speaker for seg in source_segments if seg.speaker])
        
        validated_participants = []
        for participant in participants:
            if participant.lower() in source_text or participant in source_speakers:
                validated_participants.append({
                    'name': participant,
                    'found_in_source': True,
                    'confidence': 0.9
                })
            else:
                # Check for fuzzy matching
                close_match = self._find_close_name_match(participant, source_speakers)
                validated_participants.append({
                    'name': participant,
                    'found_in_source': False,
                    'close_match': close_match,
                    'confidence': 0.5 if close_match else 0.1
                })
        
        return {
            'participants': validated_participants,
            'validation_rate': sum(1 for p in validated_participants if p['found_in_source']) / len(validated_participants)
        }
    
    def _find_close_name_match(self, name: str, source_names: set) -> Optional[str]:
        """Find close name matches using fuzzy matching."""
        best_match = None
        best_ratio = 0.7  # Minimum similarity threshold
        
        for source_name in source_names:
            ratio = difflib.SequenceMatcher(None, name.lower(), source_name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = source_name
        
        return best_match
    
    def _validate_quantitative_data(self, quant_data: Dict[str, Any], source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Validate quantitative data against source."""
        source_text = ' '.join([seg.text for seg in source_segments])
        
        validation = {
            'dates_validated': [],
            'numbers_validated': [],
            'changes_validated': []
        }
        
        # Validate dates
        dates = quant_data.get('dates', [])
        for date in dates:
            if date.lower() in source_text.lower():
                validation['dates_validated'].append({'date': date, 'found': True})
            else:
                validation['dates_validated'].append({'date': date, 'found': False})
        
        # Validate numbers
        numbers = quant_data.get('numbers', [])
        for number in numbers:
            if str(number) in source_text:
                validation['numbers_validated'].append({'number': number, 'found': True})
            else:
                validation['numbers_validated'].append({'number': number, 'found': False})
        
        return validation
    
    def _validate_owner(self, owner: str, source_segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Validate that action owner appears in meeting."""
        source_speakers = set([seg.speaker for seg in source_segments if seg.speaker])
        source_text = ' '.join([seg.text for seg in source_segments]).lower()
        
        found_as_speaker = owner in source_speakers
        mentioned_in_text = owner.lower() in source_text
        
        return {
            'owner': owner,
            'found_as_speaker': found_as_speaker,
            'mentioned_in_text': mentioned_in_text,
            'is_valid': found_as_speaker or mentioned_in_text,
            'close_match': self._find_close_name_match(owner, source_speakers) if not found_as_speaker else None
        }
    
    def _validate_date_format(self, date_str: str) -> Dict[str, Any]:
        """Validate date format and reasonableness."""
        validation = {
            'format_valid': False,
            'is_reasonable': False,
            'parsed_date': None
        }
        
        # Try to parse various date formats
        import datetime
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',  # Day names
            r'\b(next|this|last)\s+(week|month|quarter)\b',  # Relative dates
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, date_str.lower()):
                validation['format_valid'] = True
                break
        
        # Check if date is reasonable (not too far in past/future)
        if validation['format_valid']:
            validation['is_reasonable'] = True  # Simple check for now
        
        return validation


def create_validator(embedding_model=None) -> ExtractionValidator:
    """Factory function to create validator."""
    return ExtractionValidator(embedding_model)