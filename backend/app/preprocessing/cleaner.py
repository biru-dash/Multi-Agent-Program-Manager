"""Advanced transcript preprocessing and cleaning."""
import re
import os
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from app.preprocessing.parser import TranscriptSegment

# Workaround for Windows SSL certificate issues
# Disable SSL verification warnings for huggingface_hub downloads
os.environ.setdefault('HF_HUB_DISABLE_SSL_WARNING', '1')

# Try to import sentence_transformers with SSL workaround
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("Warning: sentence-transformers or sklearn not available. Topic segmentation disabled.")

from app.config.settings import settings


class TranscriptCleaner:
    """Advanced transcript cleaning and preprocessing."""
    
    # Common filler words and phrases
    FILLER_WORDS = {
        'um', 'uh', 'er', 'ah', 'hmm', 'like', 'you know', 'actually',
        'basically', 'literally', 'kind of', 'sort of', 'I mean',
        'you see', 'right', 'okay', 'so', 'well', 'yeah', 'yep',
        'sure', 'alright', 'ok', 'huh', 'wow', 'oh', 'ahh'
    }
    
    # Assignment keywords that indicate action items
    ASSIGNMENT_KEYWORDS = {
        'will do', 'will handle', 'assigned to', 'responsible for',
        'takes care of', 'will take', 'will work on', 'will review',
        'will follow up', 'will send', 'will check', 'will update'
    }
    
    # Affirmation keywords
    AFFIRMATION_KEYWORDS = {
        'yes', 'yeah', 'yep', 'confirmed', 'agreed', 'correct',
        'exactly', 'right', 'sure', 'absolutely', 'definitely'
    }
    
    def __init__(self, embedding_model_name: Optional[str] = None):
        """Initialize cleaner with optional embedding model for topic segmentation."""
        self.embedding_model = None
        if embedding_model_name and EMBEDDING_AVAILABLE:
            try:
                # Set SSL environment variables before loading
                original_curl = os.environ.get('CURL_CA_BUNDLE')
                original_requests = os.environ.get('REQUESTS_CA_BUNDLE')
                
                try:
                    # First attempt: normal loading
                    self.embedding_model = SentenceTransformer(embedding_model_name)
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if it's an SSL/certificate error
                    if any(keyword in error_str for keyword in ['ssl', 'certificate', 'cert', 'verify']):
                        print(f"Warning: SSL certificate issue detected. Attempting workaround...")
                        # Try with SSL verification disabled
                        os.environ['CURL_CA_BUNDLE'] = ''
                        os.environ['REQUESTS_CA_BUNDLE'] = ''
                        os.environ['HF_HUB_DISABLE_SSL_WARNING'] = '1'
                        
                        # Import requests and disable SSL warnings
                        try:
                            import urllib3
                            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        except:
                            pass
                        
                        # Try loading again
                        self.embedding_model = SentenceTransformer(embedding_model_name)
                        print("Successfully loaded embedding model with SSL workaround.")
                    else:
                        # Not an SSL error, re-raise
                        raise
                        
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                print("Topic segmentation will be disabled. Preprocessing will continue with other features.")
                self.embedding_model = None
        elif embedding_model_name and not EMBEDDING_AVAILABLE:
            print("Warning: Embedding model requested but dependencies not available.")
            print("Topic segmentation will be disabled.")
    
    def remove_fillers(self, text: str) -> str:
        """Remove filler words and phrases from text."""
        words = text.split()
        cleaned_words = []
        
        i = 0
        while i < len(words):
            # Check for multi-word fillers
            if i < len(words) - 1:
                two_word = f"{words[i]} {words[i+1]}".lower()
                if two_word in self.FILLER_WORDS:
                    i += 2
                    continue
                three_word = f"{words[i]} {words[i+1]} {words[i+2]}".lower() if i < len(words) - 2 else None
                if three_word and three_word in self.FILLER_WORDS:
                    i += 3
                    continue
            
            # Check single word
            if words[i].lower().rstrip('.,!?;:') not in self.FILLER_WORDS:
                cleaned_words.append(words[i])
            i += 1
        
        # Clean up extra whitespace
        cleaned_text = ' '.join(cleaned_words)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        return cleaned_text.strip()
    
    def remove_repetitions(self, text: str) -> str:
        """Remove repeated words and phrases (e.g., 'yeah yeah', 'exactly exactly')."""
        # Remove immediate repetitions
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        # Remove triple repetitions
        text = re.sub(r'\b(\w+)\s+\1\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        return text
    
    def remove_small_talk(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Remove small talk segments (greetings, acknowledgments, filler)."""
        small_talk_patterns = [
            r'^(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)',
            r'^(thanks|thank\s+you|appreciate\s+it)',
            r'^(sure|okay|ok|yep|yeah|uh\s+huh)$',
            r'^(got\s+it|understood|makes\s+sense)$',
            r'^(sounds\s+good|sounds\s+great|perfect|great)$',
        ]
        
        filtered = []
        for seg in segments:
            text_lower = seg.text.lower().strip()
            # Skip if it's just small talk
            is_small_talk = any(re.match(pattern, text_lower) for pattern in small_talk_patterns)
            
            # Also skip very short segments that are likely acknowledgments
            if len(text_lower.split()) <= 3 and is_small_talk:
                continue
            
            # Skip if it's just a single word acknowledgment
            if len(text_lower.split()) == 1 and text_lower in ['yeah', 'yep', 'ok', 'okay', 'sure', 'right']:
                continue
            
            filtered.append(seg)
        
        return filtered
    
    def merge_short_turns(self, segments: List[TranscriptSegment], min_duration_seconds: float = 3.0) -> List[TranscriptSegment]:
        """Merge consecutive segments from same speaker if they're very short."""
        if not segments:
            return segments
        
        merged = []
        current_segment = segments[0]
        
        for next_segment in segments[1:]:
            # If same speaker and current segment is short, merge
            if (current_segment.speaker == next_segment.speaker and 
                current_segment.speaker is not None and
                len(current_segment.text.split()) < 10):  # Short segment
                
                # Merge text
                merged_text = f"{current_segment.text} {next_segment.text}".strip()
                current_segment = TranscriptSegment(
                    merged_text,
                    speaker=current_segment.speaker,
                    timestamp=current_segment.timestamp
                )
            else:
                merged.append(current_segment)
                current_segment = next_segment
        
        # Add last segment
        merged.append(current_segment)
        return merged
    
    def normalize_speakers(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Normalize speaker names to canonical forms."""
        # Build speaker mapping
        speaker_variants = defaultdict(set)
        
        for segment in segments:
            if segment.speaker:
                # Extract base name (first word or first two words)
                base = segment.speaker.strip().lower()
                words = base.split()
                if len(words) >= 2:
                    # Use first name + last initial or first two words
                    base_name = f"{words[0]} {words[1]}"
                else:
                    base_name = words[0]
                
                speaker_variants[base_name].add(segment.speaker.strip())
        
        # Create canonical mapping (use most common variant as canonical)
        speaker_map = {}
        for base, variants in speaker_variants.items():
            # Find the longest/most specific variant as canonical
            canonical = max(variants, key=len)
            for variant in variants:
                speaker_map[variant] = canonical
        
        # Apply normalization
        normalized_segments = []
        for segment in segments:
            if segment.speaker and segment.speaker.strip() in speaker_map:
                normalized_speaker = speaker_map[segment.speaker.strip()]
                normalized_segments.append(
                    TranscriptSegment(segment.text, speaker=normalized_speaker, timestamp=segment.timestamp)
                )
            else:
                normalized_segments.append(segment)
        
        return normalized_segments
    
    def segment_by_topics(self, segments: List[TranscriptSegment], threshold: float = 0.7) -> List[List[TranscriptSegment]]:
        """Segment transcript into topics using sentence embeddings."""
        if not self.embedding_model:
            # If embedding model is not available, return segments as single topic
            return [segments]
        
        if len(segments) < 2:
            return [segments]
        
        # Combine segments into sliding windows
        window_size = 3
        windows = []
        window_texts = []
        
        for i in range(len(segments) - window_size + 1):
            window = segments[i:i + window_size]
            window_text = ' '.join([seg.text for seg in window])
            windows.append(window)
            window_texts.append(window_text)
        
        if len(window_texts) < 2:
            return [segments]
        
        # Generate embeddings
        try:
            embeddings = self.embedding_model.encode(window_texts)
        except Exception as e:
            print(f"Warning: Could not generate embeddings: {e}")
            return [segments]
        
        # Find topic boundaries using cosine similarity
        topic_segments = []
        current_topic = [windows[0]]
        
        for i in range(1, len(windows)):
            similarity = cosine_similarity(
                embeddings[i-1:i],
                embeddings[i:i+1]
            )[0][0]
            
            if similarity < threshold:
                # Topic shift detected
                topic_segments.append(current_topic)
                current_topic = [windows[i]]
            else:
                # Same topic, merge windows
                if windows[i] not in current_topic:
                    current_topic.append(windows[i])
        
        if current_topic:
            topic_segments.append(current_topic)
        
        # Flatten windows back to segments
        result = []
        for topic in topic_segments:
            flat_segments = []
            seen_segments = set()
            for window in topic:
                for seg in window:
                    seg_id = id(seg)
                    if seg_id not in seen_segments:
                        flat_segments.append(seg)
                        seen_segments.add(seg_id)
            result.append(flat_segments)
        
        return result if result else [segments]
    
    def semantic_chunk(self, text: str, max_tokens: int = 600, min_tokens: int = 200) -> List[str]:
        """Intelligently chunk text using semantic similarity (~500-700 tokens per chunk)."""
        if not self.embedding_model:
            # Fallback to simple chunking
            return self._simple_chunk(text, max_tokens)
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'[.!?]+\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return [text] if text.strip() else []
        
        # Generate embeddings for sentences
        try:
            sentence_embeddings = self.embedding_model.encode(sentences)
        except Exception as e:
            print(f"Warning: Could not generate embeddings for chunking: {e}")
            return self._simple_chunk(text, max_tokens)
        
        # Build chunks using semantic similarity
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for i, sentence in enumerate(sentences):
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            sentence_tokens = len(sentence) // 4
            
            # Check if adding this sentence would exceed max_tokens
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Finalize current chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            elif i == 0:
                # First sentence
                current_chunk.append(sentence)
                current_tokens = sentence_tokens
            else:
                # Check semantic similarity with previous sentence
                similarity = cosine_similarity(
                    sentence_embeddings[i-1:i],
                    sentence_embeddings[i:i+1]
                )[0][0]
                
                # If similarity is high and we haven't exceeded min_tokens, keep in same chunk
                if similarity > 0.7 and current_tokens >= min_tokens:
                    # Check if we can add without exceeding max
                    if current_tokens + sentence_tokens <= max_tokens:
                        current_chunk.append(sentence)
                        current_tokens += sentence_tokens
                    else:
                        # Start new chunk
                        chunks.append(' '.join(current_chunk))
                        current_chunk = [sentence]
                        current_tokens = sentence_tokens
                else:
                    # Low similarity or chunk too small - decide based on size
                    if current_tokens < min_tokens:
                        # Keep adding until we reach min_tokens
                        current_chunk.append(sentence)
                        current_tokens += sentence_tokens
                    else:
                        # Start new chunk
                        chunks.append(' '.join(current_chunk))
                        current_chunk = [sentence]
                        current_tokens = sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _simple_chunk(self, text: str, max_tokens: int) -> List[str]:
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
    
    def clean_segments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Apply all cleaning steps to segments."""
        cleaned = []
        for segment in segments:
            # Remove fillers
            cleaned_text = self.remove_fillers(segment.text)
            # Remove repetitions
            cleaned_text = self.remove_repetitions(cleaned_text)
            if cleaned_text:  # Only add non-empty segments
                cleaned.append(
                    TranscriptSegment(cleaned_text, speaker=segment.speaker, timestamp=segment.timestamp)
                )
        return cleaned
    
    def calculate_assignment_confidence(self, text: str) -> float:
        """Calculate confidence score for action item assignment."""
        text_lower = text.lower()
        confidence = 0.5  # Base confidence
        
        # Check for assignment keywords
        for keyword in self.ASSIGNMENT_KEYWORDS:
            if keyword in text_lower:
                confidence += 0.3
                break
        
        # Check for affirmation
        for keyword in self.AFFIRMATION_KEYWORDS:
            if keyword in text_lower:
                confidence += 0.1
                break
        
        # Check for explicit names or pronouns with action verbs
        if re.search(r'\b(I|we|you|he|she|they|John|Jane|team)\s+will\s+\w+', text_lower):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def process(self, segments: List[TranscriptSegment], 
                remove_fillers: bool = True,
                normalize_speakers: bool = True,
                segment_topics: bool = False,
                remove_small_talk: bool = True,
                merge_short_turns: bool = True) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
        """Full preprocessing pipeline."""
        processed = segments.copy()
        metadata = {
            "original_segment_count": len(segments),
            "speakers": []
        }
        
        # Step 1: Remove small talk (greetings, acknowledgments)
        if remove_small_talk:
            processed = self.remove_small_talk(processed)
            metadata["small_talk_removed"] = True
        
        # Step 2: Merge short consecutive turns from same speaker
        if merge_short_turns:
            processed = self.merge_short_turns(processed)
            metadata["short_turns_merged"] = True
        
        # Step 3: Remove fillers and repetitions
        if remove_fillers:
            processed = self.clean_segments(processed)
            metadata["filler_removed"] = True
        
        # Step 4: Normalize speakers
        if normalize_speakers:
            processed = self.normalize_speakers(processed)
            metadata["speakers"] = list(set([seg.speaker for seg in processed if seg.speaker]))
            metadata["speaker_normalized"] = True
        
        # Step 5: Segment by topics (optional)
        if segment_topics and self.embedding_model:
            topic_segments = self.segment_by_topics(processed)
            metadata["topic_segments"] = len(topic_segments)
            # Flatten for return, but store topic info
            processed = [seg for topic in topic_segments for seg in topic]
        
        metadata["final_segment_count"] = len(processed)
        return processed, metadata


def get_cleaner(embedding_model_name: Optional[str] = None) -> TranscriptCleaner:
    """Factory function to get TranscriptCleaner with optional embedding model."""
    # Check if we should skip embedding model entirely
    skip_embedding = os.environ.get('MIA_SKIP_EMBEDDING_MODEL', 'false').lower() == 'true'
    
    if skip_embedding:
        print("[get_cleaner] Skipping embedding model (MIA_SKIP_EMBEDDING_MODEL=true)")
        return TranscriptCleaner(embedding_model_name=None)
    
    model_name = embedding_model_name or settings.embedding_model
    return TranscriptCleaner(model_name)
