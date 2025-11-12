"""Enhanced preprocessing pipeline with all new components."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from app.preprocessing.parser import TranscriptSegment, TranscriptParser
from app.preprocessing.cleaner import TranscriptCleaner
from app.models.model_manager import model_manager
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EnhancedPreprocessingPipeline:
    """Enhanced preprocessing pipeline with diarization, punctuation restoration, etc."""
    
    def __init__(self):
        """Initialize the enhanced preprocessing pipeline."""
        self.model_manager = model_manager
        self.components = {}
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all preprocessing components."""
        try:
            # Get models for each step
            self.components['diarizer'] = self.model_manager.get_model_for_step('diarization')
            self.components['punctuation'] = self.model_manager.get_model_for_step('punctuation')
            self.components['embedding'] = self.model_manager.get_model_for_step('embedding')
            self.components['entity_recognition'] = self.model_manager.get_model_for_step('entity_recognition')
            
            logger.info("Enhanced preprocessing pipeline initialized successfully")
            
        except Exception as e:
            logger.warning(f"Some components failed to initialize: {e}")
            # Continue with available components
    
    def process_transcript(
        self,
        file_path: str,
        audio_path: Optional[str] = None,
        calendar_metadata: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, bool]] = None
    ) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
        """Process transcript through the enhanced pipeline.
        
        Args:
            file_path: Path to transcript file
            audio_path: Optional path to audio file for diarization
            calendar_metadata: Meeting metadata with participant names
            options: Processing options
            
        Returns:
            Tuple of (processed_segments, metadata)
        """
        if options is None:
            options = {
                'enable_diarization': True,
                'enable_punctuation_restoration': True,
                'enable_coreference_resolution': True,
                'enable_enhanced_chunking': True,
                'remove_fillers': True,
                'normalize_speakers': True
            }
        
        metadata = {
            'pipeline_version': '2.0',
            'components_used': [],
            'processing_steps': []
        }
        
        # Step 1: Parse transcript
        segments = TranscriptParser.parse(file_path)
        metadata['original_segments'] = len(segments)
        metadata['processing_steps'].append('parsing')
        
        # Step 2: Speaker diarization (if audio available)
        if audio_path and options.get('enable_diarization', True):
            segments = self._apply_diarization(segments, audio_path, calendar_metadata, metadata)
        
        # Step 3: Punctuation restoration
        if options.get('enable_punctuation_restoration', True):
            segments = self._apply_punctuation_restoration(segments, metadata)
        
        # Step 4: Coreference resolution
        if options.get('enable_coreference_resolution', True):
            segments = self._apply_coreference_resolution(segments, metadata)
        
        # Step 5: Traditional cleaning (with enhancements)
        cleaner = TranscriptCleaner(
            embedding_model_name=settings.models['embedding']['model']
        )
        
        segments, cleaning_metadata = cleaner.process(
            segments,
            remove_fillers=options.get('remove_fillers', True),
            normalize_speakers=options.get('normalize_speakers', True),
            segment_topics=options.get('enable_enhanced_chunking', True),
            remove_small_talk=True,
            merge_short_turns=True
        )
        
        metadata.update(cleaning_metadata)
        metadata['final_segments'] = len(segments)
        
        return segments, metadata
    
    def _apply_diarization(
        self, 
        segments: List[TranscriptSegment], 
        audio_path: str,
        calendar_metadata: Optional[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[TranscriptSegment]:
        """Apply speaker diarization if available."""
        try:
            diarizer = self.components.get('diarizer')
            if not diarizer:
                logger.warning("Diarizer not available, skipping diarization")
                return segments
            
            # Check if it's PyAnnote diarizer (has audio processing)
            if hasattr(diarizer, 'diarize_audio'):
                # Audio-based diarization
                logger.info("Applying audio-based diarization")
                diarization_segments = diarizer.diarize_audio(audio_path)
                segments = diarizer.assign_speakers_to_segments(segments, diarization_segments)
                
                # Resolve speaker names using calendar
                if calendar_metadata:
                    segments = diarizer.resolve_speaker_names(segments, calendar_metadata)
                
                metadata['components_used'].append('audio_diarization')
                metadata['diarization_segments'] = len(diarization_segments)
            
            else:
                # Text-based diarization (SimpleDiarizer)
                logger.info("Applying text-based speaker normalization")
                segments = diarizer.normalize_speakers(segments)
                metadata['components_used'].append('text_diarization')
            
            metadata['processing_steps'].append('diarization')
            return segments
            
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            metadata['diarization_error'] = str(e)
            return segments
    
    def _apply_punctuation_restoration(
        self, 
        segments: List[TranscriptSegment], 
        metadata: Dict[str, Any]
    ) -> List[TranscriptSegment]:
        """Apply punctuation restoration."""
        try:
            punctuation_model = self.components.get('punctuation')
            if not punctuation_model:
                logger.warning("Punctuation model not available")
                return segments
            
            logger.info("Applying punctuation restoration")
            
            # Check if it's the full model or rule-based
            if hasattr(punctuation_model, 'restore_segments'):
                segments = punctuation_model.restore_segments(segments)
                metadata['components_used'].append('punctuation_model')
            else:
                # Rule-based fallback
                for i, segment in enumerate(segments):
                    if segment.text:
                        restored_text = punctuation_model.restore_punctuation(segment.text)
                        segments[i] = TranscriptSegment(
                            text=restored_text,
                            speaker=segment.speaker,
                            timestamp=segment.timestamp
                        )
                metadata['components_used'].append('punctuation_rules')
            
            metadata['processing_steps'].append('punctuation_restoration')
            return segments
            
        except Exception as e:
            logger.error(f"Punctuation restoration failed: {e}")
            metadata['punctuation_error'] = str(e)
            return segments
    
    def _apply_coreference_resolution(
        self, 
        segments: List[TranscriptSegment], 
        metadata: Dict[str, Any]
    ) -> List[TranscriptSegment]:
        """Apply coreference resolution."""
        try:
            # Use built-in coreference resolver for now
            from app.models.punctuation import CoreferenceResolver
            
            logger.info("Applying coreference resolution")
            resolver = CoreferenceResolver()
            segments = resolver.resolve_coreferences(segments)
            
            metadata['components_used'].append('coreference_resolution')
            metadata['processing_steps'].append('coreference_resolution')
            return segments
            
        except Exception as e:
            logger.error(f"Coreference resolution failed: {e}")
            metadata['coreference_error'] = str(e)
            return segments
    
    def process_audio_file(
        self,
        audio_path: str,
        output_transcript_path: Optional[str] = None,
        calendar_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
        """Process audio file from scratch (ASR + full pipeline).
        
        Args:
            audio_path: Path to audio file
            output_transcript_path: Where to save transcript
            calendar_metadata: Meeting metadata
            
        Returns:
            Tuple of (processed_segments, metadata)
        """
        metadata = {
            'input_type': 'audio',
            'audio_path': audio_path,
            'pipeline_version': '2.0'
        }
        
        try:
            # Step 1: ASR (if needed)
            transcript_path = self._transcribe_audio(audio_path, output_transcript_path, metadata)
            
            # Step 2: Full processing pipeline
            segments, processing_metadata = self.process_transcript(
                transcript_path,
                audio_path=audio_path,
                calendar_metadata=calendar_metadata
            )
            
            metadata.update(processing_metadata)
            return segments, metadata
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            metadata['error'] = str(e)
            return [], metadata
    
    def _transcribe_audio(
        self, 
        audio_path: str, 
        output_path: Optional[str],
        metadata: Dict[str, Any]
    ) -> str:
        """Transcribe audio file using ASR."""
        try:
            # Try to use Whisper if available
            import whisper
            
            logger.info("Transcribing audio with Whisper")
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            
            # Convert to segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "speaker": None  # Will be assigned later
                })
            
            # Save transcript
            transcript_path = output_path or audio_path.replace('.wav', '.json').replace('.mp3', '.json')
            
            import json
            with open(transcript_path, 'w') as f:
                json.dump({
                    "transcript": segments,
                    "language": result.get("language"),
                    "duration": len(segments)
                }, f, indent=2)
            
            metadata['asr_model'] = 'whisper-base'
            metadata['asr_language'] = result.get("language")
            metadata['asr_segments'] = len(segments)
            metadata['components_used'].append('whisper_asr')
            
            return transcript_path
            
        except ImportError:
            logger.error("Whisper not available for ASR")
            raise RuntimeError("ASR capability not available - install whisper-openai")
        except Exception as e:
            logger.error(f"ASR failed: {e}")
            raise
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status of all pipeline components."""
        status = {
            'pipeline_version': '2.0',
            'components': {},
            'capabilities': {
                'audio_processing': False,
                'diarization': False,
                'punctuation_restoration': False,
                'coreference_resolution': False,
                'semantic_chunking': False
            }
        }
        
        # Check component status
        for component_name, component in self.components.items():
            if component:
                status['components'][component_name] = {
                    'status': 'available',
                    'type': type(component).__name__
                }
                
                # Update capabilities
                if component_name == 'diarizer':
                    status['capabilities']['diarization'] = True
                elif component_name == 'punctuation':
                    status['capabilities']['punctuation_restoration'] = True
            else:
                status['components'][component_name] = {
                    'status': 'unavailable',
                    'type': None
                }
        
        # Check for additional capabilities
        try:
            import whisper
            status['capabilities']['audio_processing'] = True
        except ImportError:
            pass
        
        status['capabilities']['coreference_resolution'] = True  # Built-in
        status['capabilities']['semantic_chunking'] = bool(self.components.get('embedding'))
        
        return status
    
    def update_component_model(self, component: str, provider: str, model: str):
        """Update model for a specific component."""
        try:
            # Update configuration
            self.model_manager.update_model_config(component, provider, model)
            
            # Reload component
            self.components[component] = self.model_manager.get_model_for_step(component)
            
            logger.info(f"Updated {component} model to {provider}/{model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update {component} model: {e}")
            return False


# Global instance
enhanced_pipeline = EnhancedPreprocessingPipeline()