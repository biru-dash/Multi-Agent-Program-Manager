"""Punctuation restoration models for cleaning ASR output."""
import logging
import re
from typing import List, Dict, Any, Optional
from app.preprocessing.parser import TranscriptSegment

logger = logging.getLogger(__name__)


class PunctuationModel:
    """Advanced punctuation restoration using transformer models."""
    
    def __init__(self, model_name: str = "oliverguhr/fullstop-punctuation-multilang-large"):
        """Initialize punctuation model.
        
        Args:
            model_name: HuggingFace model name for punctuation restoration
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the punctuation restoration model."""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            from transformers import pipeline
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            
            # Create pipeline
            self.model = pipeline(
                "token-classification",
                model=model,
                tokenizer=self.tokenizer,
                aggregation_strategy="first"
            )
            
            logger.info(f"Loaded punctuation model: {self.model_name}")
            
        except ImportError:
            logger.error("transformers not installed. Install with: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load punctuation model: {e}")
            raise
    
    def restore_punctuation(self, text: str) -> str:
        """Restore punctuation in text.
        
        Args:
            text: Text without proper punctuation
            
        Returns:
            Text with restored punctuation
        """
        if not self.model:
            raise RuntimeError("Punctuation model not loaded")
        
        try:
            # Preprocess text
            text = self._preprocess_text(text)
            
            # Apply model
            predictions = self.model(text)
            
            # Reconstruct text with punctuation
            restored_text = self._apply_punctuation(text, predictions)
            
            # Post-process
            restored_text = self._postprocess_text(restored_text)
            
            return restored_text
            
        except Exception as e:
            logger.error(f"Punctuation restoration failed: {e}")
            # Fallback to rule-based
            return RuleBasedPunctuation().restore_punctuation(text)
    
    def restore_segments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Restore punctuation for all segments.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            Segments with restored punctuation
        """
        restored_segments = []
        
        for segment in segments:
            if segment.text:
                restored_text = self.restore_punctuation(segment.text)
                restored_segments.append(TranscriptSegment(
                    text=restored_text,
                    speaker=segment.speaker,
                    timestamp=segment.timestamp
                ))
            else:
                restored_segments.append(segment)
        
        return restored_segments
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for punctuation model."""
        # Remove existing punctuation to avoid bias
        text = re.sub(r'[.!?,:;]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Lowercase (many models expect lowercase)
        text = text.lower()
        
        return text
    
    def _apply_punctuation(self, text: str, predictions: List[Dict]) -> str:
        """Apply punctuation predictions to text."""
        words = text.split()
        result = []
        
        # Create word-to-prediction mapping
        pred_map = {}
        for pred in predictions:
            word = pred['word'].replace('▁', '').replace('#', '')  # Handle subword tokens
            if word in words:
                pred_map[word] = pred['entity_group']
        
        for i, word in enumerate(words):
            result.append(word)
            
            # Add punctuation based on prediction
            if word in pred_map:
                entity = pred_map[word]
                if entity == 'PERIOD':
                    result.append('.')
                elif entity == 'COMMA':
                    result.append(',')
                elif entity == 'QUESTION':
                    result.append('?')
                elif entity == 'EXCLAMATION':
                    result.append('!')
        
        return ' '.join(result)
    
    def _postprocess_text(self, text: str) -> str:
        """Post-process restored text."""
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)
        
        # Capitalize after sentence endings
        sentences = re.split(r'([.!?]+)', text)
        result = []
        
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part.strip():  # Text part
                # Capitalize first word
                words = part.strip().split()
                if words:
                    words[0] = words[0].capitalize()
                    result.append(' '.join(words))
            elif part.strip():  # Punctuation part
                result.append(part)
        
        return ''.join(result)


class RuleBasedPunctuation:
    """Rule-based punctuation restoration fallback."""
    
    def __init__(self):
        """Initialize rule-based punctuation restorer."""
        self.sentence_endings = {
            'question_words': ['what', 'how', 'when', 'where', 'who', 'why', 'which', 'whose'],
            'statement_indicators': ['we', 'I', 'they', 'the', 'this', 'that'],
        }
    
    def restore_punctuation(self, text: str) -> str:
        """Apply rule-based punctuation restoration.
        
        Args:
            text: Text without proper punctuation
            
        Returns:
            Text with basic punctuation
        """
        if not text:
            return text
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Split into potential sentences
        sentences = self._split_into_sentences(text)
        
        # Apply punctuation rules
        punctuated_sentences = []
        for sentence in sentences:
            if sentence.strip():
                punctuated = self._punctuate_sentence(sentence.strip())
                punctuated_sentences.append(punctuated)
        
        return ' '.join(punctuated_sentences)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into potential sentences."""
        # Split on long pauses (multiple spaces) or discourse markers
        discourse_markers = ['so', 'well', 'anyway', 'however', 'but', 'and then']
        
        # Simple split on potential sentence boundaries
        sentences = []
        current = []
        words = text.split()
        
        for i, word in enumerate(words):
            current.append(word)
            
            # Check for sentence boundary indicators
            if (len(current) > 6 and  # Minimum sentence length
                (word.lower() in discourse_markers or
                 (i < len(words) - 1 and words[i + 1].lower() in discourse_markers))):
                sentences.append(' '.join(current))
                current = []
        
        # Add remaining words
        if current:
            sentences.append(' '.join(current))
        
        return sentences
    
    def _punctuate_sentence(self, sentence: str) -> str:
        """Add punctuation to a single sentence."""
        words = sentence.split()
        if not words:
            return sentence
        
        # Capitalize first word
        words[0] = words[0].capitalize()
        
        # Determine sentence type and ending
        first_word = words[0].lower()
        
        if first_word in self.sentence_endings['question_words']:
            # Question
            ending = '?'
        elif any(indicator in sentence.lower() for indicator in ['please', 'can you', 'could you']):
            # Request/question
            ending = '?'
        else:
            # Statement
            ending = '.'
        
        # Add commas for long sentences
        result = self._add_commas(words)
        
        # Add final punctuation
        if not result.endswith(('.', '!', '?')):
            result += ending
        
        return result
    
    def _add_commas(self, words: List[str]) -> str:
        """Add commas to long sentences."""
        if len(words) < 8:
            return ' '.join(words)
        
        result = []
        for i, word in enumerate(words):
            result.append(word)
            
            # Add comma after discourse markers
            if (word.lower() in ['however', 'therefore', 'furthermore', 'moreover'] and
                i < len(words) - 1):
                result.append(',')
            
            # Add comma before conjunctions in long sentences
            elif (word.lower() in ['and', 'but', 'or'] and
                  len(words) > 10 and i > 3 and i < len(words) - 3):
                result.insert(-1, ',')
        
        return ' '.join(result)


class CoreferenceResolver:
    """Coreference resolution for replacing pronouns with names."""
    
    def __init__(self):
        """Initialize coreference resolver."""
        self.pronouns = ['he', 'she', 'they', 'it', 'his', 'her', 'their', 'him', 'them']
    
    def resolve_coreferences(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Resolve pronouns to actual speaker names.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            Segments with resolved coreferences
        """
        # Build speaker context
        speaker_context = self._build_speaker_context(segments)
        
        # Resolve pronouns in each segment
        resolved_segments = []
        
        for i, segment in enumerate(segments):
            if segment.text and segment.speaker:
                resolved_text = self._resolve_segment_pronouns(
                    segment.text,
                    segment.speaker,
                    speaker_context,
                    i,
                    segments
                )
                resolved_segments.append(TranscriptSegment(
                    text=resolved_text,
                    speaker=segment.speaker,
                    timestamp=segment.timestamp
                ))
            else:
                resolved_segments.append(segment)
        
        return resolved_segments
    
    def _build_speaker_context(self, segments: List[TranscriptSegment]) -> Dict[str, Any]:
        """Build context about speakers mentioned in the meeting."""
        context = {
            'speakers': set(),
            'speaker_mentions': {},
            'speaker_genders': {}
        }
        
        for segment in segments:
            if segment.speaker:
                context['speakers'].add(segment.speaker)
                
                # Track mentions of other speakers
                for speaker in context['speakers']:
                    if speaker.lower() in segment.text.lower() and speaker != segment.speaker:
                        if speaker not in context['speaker_mentions']:
                            context['speaker_mentions'][speaker] = []
                        context['speaker_mentions'][speaker].append(segment.speaker)
        
        return context
    
    def _resolve_segment_pronouns(
        self,
        text: str,
        current_speaker: str,
        context: Dict[str, Any],
        segment_idx: int,
        all_segments: List[TranscriptSegment]
    ) -> str:
        """Resolve pronouns in a single segment."""
        words = text.split()
        result = []
        
        for i, word in enumerate(words):
            word_lower = word.lower().strip('.,!?')
            
            if word_lower in self.pronouns:
                # Try to resolve pronoun
                resolved = self._resolve_pronoun(
                    word_lower,
                    current_speaker,
                    context,
                    segment_idx,
                    all_segments
                )
                result.append(resolved or word)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def _resolve_pronoun(
        self,
        pronoun: str,
        current_speaker: str,
        context: Dict[str, Any],
        segment_idx: int,
        all_segments: List[TranscriptSegment]
    ) -> Optional[str]:
        """Resolve a specific pronoun to a name."""
        # Simple heuristics for pronoun resolution
        
        # "I" always refers to current speaker
        if pronoun == 'i':
            return current_speaker
        
        # Look at recent context (last 3 segments)
        recent_speakers = []
        for i in range(max(0, segment_idx - 3), segment_idx):
            if all_segments[i].speaker and all_segments[i].speaker != current_speaker:
                recent_speakers.append(all_segments[i].speaker)
        
        # If only one other recent speaker, likely refers to them
        if len(set(recent_speakers)) == 1:
            return recent_speakers[0]
        
        # For now, don't resolve ambiguous cases
        return None


def get_punctuation_model(provider: str = "local", **kwargs) -> Any:
    """Factory function to get punctuation model."""
    if provider == "local" or provider == "punctuation":
        model_name = kwargs.get('model_name', 'oliverguhr/fullstop-punctuation-multilang-large')
        return PunctuationModel(model_name)
    elif provider == "rule_based":
        return RuleBasedPunctuation()
    else:
        raise ValueError(f"Unknown punctuation provider: {provider}")