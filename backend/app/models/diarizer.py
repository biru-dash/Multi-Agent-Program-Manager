"""Speaker diarization models for identifying who spoke when."""
import logging
import re
from typing import List, Dict, Any, Tuple, Optional, Union
from pathlib import Path
import numpy as np
from app.preprocessing.parser import TranscriptSegment

logger = logging.getLogger(__name__)


class PyAnnoteDiarizer:
    """PyAnnote-based speaker diarization with calendar integration."""
    
    def __init__(self, model_name: str = "pyannote/speaker-diarization-3.1", auth_token: Optional[str] = None):
        """Initialize PyAnnote diarizer.
        
        Args:
            model_name: HuggingFace model name
            auth_token: HuggingFace auth token for gated models
        """
        self.model_name = model_name
        self.pipeline = None
        self.auth_token = auth_token
        self._load_model()
    
    def _load_model(self):
        """Load the diarization pipeline."""
        try:
            from pyannote.audio import Pipeline
            
            if self.auth_token:
                self.pipeline = Pipeline.from_pretrained(
                    self.model_name, 
                    use_auth_token=self.auth_token
                )
            else:
                self.pipeline = Pipeline.from_pretrained(self.model_name)
            
            logger.info(f"Loaded PyAnnote diarization model: {self.model_name}")
            
        except ImportError:
            logger.error("pyannote.audio not installed. Install with: pip install pyannote.audio")
            raise
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            raise
    
    def diarize_audio(self, audio_path: str) -> List[Tuple[float, float, str]]:
        """Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of (start_time, end_time, speaker_id) tuples
        """
        if not self.pipeline:
            raise RuntimeError("Diarization pipeline not loaded")
        
        try:
            # Apply diarization
            diarization = self.pipeline(audio_path)
            
            # Convert to segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append((
                    turn.start,
                    turn.end, 
                    speaker
                ))
            
            logger.info(f"Diarization found {len(segments)} speaker segments")
            return segments
            
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []
    
    def assign_speakers_to_segments(
        self, 
        segments: List[TranscriptSegment], 
        diarization_segments: List[Tuple[float, float, str]]
    ) -> List[TranscriptSegment]:
        """Assign speaker IDs to transcript segments based on timestamps.
        
        Args:
            segments: Original transcript segments
            diarization_segments: Diarization output
            
        Returns:
            Segments with updated speaker information
        """
        updated_segments = []
        
        for segment in segments:
            # Try to parse timestamp to get start time
            start_time = self._parse_timestamp(segment.timestamp)
            
            if start_time is not None:
                # Find matching diarization segment
                speaker_id = self._find_speaker_at_time(start_time, diarization_segments)
                updated_segment = TranscriptSegment(
                    text=segment.text,
                    speaker=speaker_id or segment.speaker,
                    timestamp=segment.timestamp
                )
            else:
                updated_segment = segment
            
            updated_segments.append(updated_segment)
        
        return updated_segments
    
    def resolve_speaker_names(
        self, 
        segments: List[TranscriptSegment], 
        calendar_metadata: Dict[str, Any]
    ) -> List[TranscriptSegment]:
        """Resolve speaker IDs to actual names using calendar data.
        
        Args:
            segments: Segments with speaker IDs
            calendar_metadata: Meeting metadata with participant names
            
        Returns:
            Segments with resolved speaker names
        """
        participants = calendar_metadata.get('participants', [])
        if not participants:
            logger.warning("No participant names in calendar metadata")
            return segments
        
        # Build speaker ID to name mapping
        speaker_mapping = self._build_speaker_mapping(segments, participants)
        
        # Apply mapping
        resolved_segments = []
        for segment in segments:
            if segment.speaker and segment.speaker in speaker_mapping:
                resolved_name = speaker_mapping[segment.speaker]
                resolved_segment = TranscriptSegment(
                    text=segment.text,
                    speaker=resolved_name,
                    timestamp=segment.timestamp
                )
            else:
                resolved_segment = segment
            
            resolved_segments.append(resolved_segment)
        
        return resolved_segments
    
    def _parse_timestamp(self, timestamp: Optional[str]) -> Optional[float]:
        """Parse timestamp string to seconds."""
        if not timestamp:
            return None
        
        # Handle formats: "1:23", "0:03", "1:23:45"
        try:
            parts = timestamp.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return float(timestamp)  # Assume seconds
        except ValueError:
            logger.warning(f"Could not parse timestamp: {timestamp}")
            return None
    
    def _find_speaker_at_time(
        self, 
        time: float, 
        diarization_segments: List[Tuple[float, float, str]]
    ) -> Optional[str]:
        """Find which speaker was active at a given time."""
        for start, end, speaker in diarization_segments:
            if start <= time <= end:
                return speaker
        return None
    
    def _build_speaker_mapping(
        self, 
        segments: List[TranscriptSegment], 
        participants: List[str]
    ) -> Dict[str, str]:
        """Build mapping from speaker IDs to participant names.
        
        Uses heuristics like:
        - Most frequent speaker -> meeting organizer/first participant
        - Speaker order -> participant order
        - Text analysis for name mentions
        """
        # Count speaker frequencies
        speaker_counts = {}
        for segment in segments:
            if segment.speaker:
                speaker_counts[segment.speaker] = speaker_counts.get(segment.speaker, 0) + 1
        
        # Sort speakers by frequency (most active first)
        sorted_speakers = sorted(speaker_counts.keys(), key=lambda s: speaker_counts[s], reverse=True)
        
        # Simple mapping: most frequent speakers -> first participants
        mapping = {}
        for i, speaker_id in enumerate(sorted_speakers):
            if i < len(participants):
                mapping[speaker_id] = participants[i]
            else:
                mapping[speaker_id] = f"Speaker_{i+1}"
        
        logger.info(f"Built speaker mapping: {mapping}")
        return mapping


class SimpleDiarizer:
    """Simple rule-based diarizer for pre-formatted transcripts."""
    
    def __init__(self):
        """Initialize simple diarizer."""
        self.speaker_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):',  # "John Doe:"
            r'^\[([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\]',  # "[John Doe]"
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+:\d+)',  # "John Doe 1:23"
        ]
    
    def diarize_text(self, text: str) -> List[TranscriptSegment]:
        """Extract speakers from formatted text transcript.
        
        Args:
            text: Raw transcript text
            
        Returns:
            List of segments with speaker information
        """
        lines = text.split('\n')
        segments = []
        current_speaker = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to detect speaker
            speaker = self._extract_speaker(line)
            
            if speaker:
                # Save previous segment
                if current_text and current_speaker:
                    segments.append(TranscriptSegment(
                        text=' '.join(current_text),
                        speaker=current_speaker,
                        timestamp=None
                    ))
                
                # Start new segment
                current_speaker = speaker
                # Remove speaker prefix from text
                clean_text = self._remove_speaker_prefix(line)
                current_text = [clean_text] if clean_text else []
            else:
                # Continue current segment
                if line:
                    current_text.append(line)
        
        # Save final segment
        if current_text and current_speaker:
            segments.append(TranscriptSegment(
                text=' '.join(current_text),
                speaker=current_speaker,
                timestamp=None
            ))
        
        return segments
    
    def _extract_speaker(self, line: str) -> Optional[str]:
        """Extract speaker name from line."""
        for pattern in self.speaker_patterns:
            match = re.match(pattern, line)
            if match:
                return match.group(1).strip()
        return None
    
    def _remove_speaker_prefix(self, line: str) -> str:
        """Remove speaker prefix from line."""
        for pattern in self.speaker_patterns:
            line = re.sub(pattern, '', line).strip()
        return line.lstrip(':').strip()
    
    def normalize_speakers(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Normalize speaker names to consistent format."""
        # Build speaker variants mapping
        speaker_variants = {}
        all_speakers = [seg.speaker for seg in segments if seg.speaker]
        
        for speaker in set(all_speakers):
            # Normalize to "First Last" format
            normalized = self._normalize_speaker_name(speaker)
            speaker_variants[speaker] = normalized
        
        # Apply normalization
        normalized_segments = []
        for segment in segments:
            if segment.speaker:
                normalized_speaker = speaker_variants.get(segment.speaker, segment.speaker)
                normalized_segments.append(TranscriptSegment(
                    text=segment.text,
                    speaker=normalized_speaker,
                    timestamp=segment.timestamp
                ))
            else:
                normalized_segments.append(segment)
        
        return normalized_segments
    
    def _normalize_speaker_name(self, name: str) -> str:
        """Normalize speaker name to consistent format."""
        if not name:
            return name
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Handle "Last, First" format
        if ',' in name:
            parts = name.split(',')
            if len(parts) == 2:
                last, first = [p.strip() for p in parts]
                return f"{first} {last}"
        
        # Handle initials and titles
        name = re.sub(r'\b[A-Z]\.\s*', '', name)  # Remove initials like "J. "
        name = re.sub(r'\b(Dr|Mr|Ms|Mrs)\.\s*', '', name, flags=re.IGNORECASE)  # Remove titles
        
        return name.strip()


def get_diarizer(provider: str = "simple", **kwargs) -> Union[PyAnnoteDiarizer, SimpleDiarizer]:
    """Factory function to get appropriate diarizer."""
    if provider == "pyannote":
        return PyAnnoteDiarizer(**kwargs)
    elif provider == "simple":
        return SimpleDiarizer()
    else:
        raise ValueError(f"Unknown diarizer provider: {provider}")