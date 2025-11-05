"""Multi-format transcript parser."""
import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import timedelta


class TranscriptSegment:
    """Represents a single segment of transcript with speaker and timestamp."""
    def __init__(self, text: str, speaker: Optional[str] = None, timestamp: Optional[str] = None):
        self.text = text.strip()
        self.speaker = speaker
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary."""
        return {
            "text": self.text,
            "speaker": self.speaker,
            "timestamp": self.timestamp
        }


class TranscriptParser:
    """Parser for multiple transcript formats."""
    
    @staticmethod
    def parse_txt(file_path: str) -> List[TranscriptSegment]:
        """Parse plain text transcript."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        segments = []
        lines = content.split('\n')
        
        current_speaker = None
        current_timestamp = None
        current_text = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Empty line - save current segment if we have text
                if current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        segments.append(TranscriptSegment(
                            text, 
                            speaker=current_speaker, 
                            timestamp=current_timestamp
                        ))
                    current_text = []
                    current_speaker = None
                    current_timestamp = None
                continue
            
            # Pattern 1: "Last, First   timestamp" format (e.g., "Chen, David   0:03")
            # Also handles "Last, First (Role)   timestamp"
            speaker_timestamp_match = re.match(r'^([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)+(?:\s+\([^)]+\))?)\s+(\d{1,2}:\d{2}(?::\d{2})?)$', line)
            if not speaker_timestamp_match:
                # Try pattern without comma: "First Last   timestamp"
                speaker_timestamp_match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+\([^)]+\))?)\s+(\d{1,2}:\d{2}(?::\d{2})?)$', line)
            if speaker_timestamp_match:
                # Save previous segment if exists
                if current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        segments.append(TranscriptSegment(
                            text, 
                            speaker=current_speaker, 
                            timestamp=current_timestamp
                        ))
                    current_text = []
                
                # Extract speaker name - handle "Last, First" or "Last, First (Role)"
                speaker_part = speaker_timestamp_match.group(1).strip()
                # Remove role in parentheses if present
                speaker_part = re.sub(r'\s*\([^)]+\)$', '', speaker_part)
                # Convert "Last, First" to "First Last" or keep as is
                if ',' in speaker_part:
                    parts = [p.strip() for p in speaker_part.split(',')]
                    if len(parts) == 2:
                        current_speaker = f"{parts[1]} {parts[0]}".strip()
                    else:
                        current_speaker = speaker_part
                else:
                    current_speaker = speaker_part
                
                current_timestamp = speaker_timestamp_match.group(2).strip()
                continue
            
            # Pattern 2: "Speaker: text" or "[Speaker] text"
            speaker_match = re.match(r'^(\w+(?:\s+\w+)?)[:\[]\s*(.+)$', line)
            if speaker_match:
                # Save previous segment
                if current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        segments.append(TranscriptSegment(
                            text, 
                            speaker=current_speaker, 
                            timestamp=current_timestamp
                        ))
                    current_text = []
                
                current_speaker = speaker_match.group(1).strip()
                text = speaker_match.group(2).strip(']')
                current_text.append(text)
                continue
            
            # Pattern 3: Lines that look like timestamps (e.g., "0:03", "1:15")
            timestamp_only_match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)$', line)
            if timestamp_only_match and not current_text:
                current_timestamp = timestamp_only_match.group(1)
                continue
            
            # Regular text line - append to current segment
            if line:
                current_text.append(line)
        
        # Save last segment
        if current_text:
            text = ' '.join(current_text).strip()
            if text:
                segments.append(TranscriptSegment(
                    text, 
                    speaker=current_speaker, 
                    timestamp=current_timestamp
                ))
        
        return segments
    
    @staticmethod
    def parse_json(file_path: str) -> List[TranscriptSegment]:
        """Parse JSON format transcript."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = []
        
        # Handle different JSON structures
        if isinstance(data, dict):
            transcript = data.get('transcript', [])
            speakers = data.get('speakers', [])
            timestamps = data.get('timestamps', [])
            
            if isinstance(transcript, list):
                for i, item in enumerate(transcript):
                    if isinstance(item, dict):
                        text = item.get('text', item.get('content', ''))
                        speaker = item.get('speaker', speakers[i] if i < len(speakers) else None)
                        timestamp = item.get('timestamp', timestamps[i] if i < len(timestamps) else None)
                        segments.append(TranscriptSegment(text, speaker=speaker, timestamp=timestamp))
                    elif isinstance(item, str):
                        speaker = speakers[i] if i < len(speakers) else None
                        timestamp = timestamps[i] if i < len(timestamps) else None
                        segments.append(TranscriptSegment(item, speaker=speaker, timestamp=timestamp))
            elif isinstance(transcript, str):
                segments.append(TranscriptSegment(transcript))
        
        return segments
    
    @staticmethod
    def parse_srt(file_path: str) -> List[TranscriptSegment]:
        """Parse SRT subtitle format."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        segments = []
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            # Parse timestamp line (format: 00:00:00,000 --> 00:00:05,000)
            timestamp_match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
            timestamp = lines[1] if timestamp_match else None
            
            # Combine text lines (skip index and timestamp lines)
            text_lines = [line.strip() for line in lines[2:] if line.strip()]
            text = ' '.join(text_lines)
            
            # Try to extract speaker from text (common pattern: "[Speaker Name] text")
            speaker_match = re.match(r'\[([^\]]+)\]\s*(.+)$', text)
            if speaker_match:
                speaker = speaker_match.group(1)
                text = speaker_match.group(2)
                segments.append(TranscriptSegment(text, speaker=speaker, timestamp=timestamp))
            else:
                segments.append(TranscriptSegment(text, timestamp=timestamp))
        
        return segments
    
    @staticmethod
    def auto_detect_format(file_path: str) -> str:
        """Auto-detect transcript format based on file extension and content."""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.json':
            return 'json'
        elif ext == '.srt':
            return 'srt'
        elif ext == '.txt' or ext == '':
            # Check content for SRT pattern
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join([f.readline() for _ in range(5)])
                if re.search(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', first_lines):
                    return 'srt'
            return 'txt'
        
        return 'txt'
    
    @staticmethod
    def parse(file_path: str, format: Optional[str] = None) -> List[TranscriptSegment]:
        """Parse transcript file with auto-detection."""
        if format is None:
            format = TranscriptParser.auto_detect_format(file_path)
        
        if format == 'json':
            return TranscriptParser.parse_json(file_path)
        elif format == 'srt':
            return TranscriptParser.parse_srt(file_path)
        else:
            return TranscriptParser.parse_txt(file_path)
    
    @staticmethod
    def to_text(segments: List[TranscriptSegment]) -> str:
        """Convert segments back to plain text."""
        lines = []
        for segment in segments:
            if segment.speaker:
                lines.append(f"{segment.speaker}: {segment.text}")
            else:
                lines.append(segment.text)
        return '\n'.join(lines)
    
    @staticmethod
    def get_speakers(segments: List[TranscriptSegment]) -> List[str]:
        """Extract unique speaker names from segments."""
        speakers = set()
        for segment in segments:
            if segment.speaker:
                speakers.add(segment.speaker.strip())
        return sorted(list(speakers))
