"""Centralized model manager for step-specific model selection and loading."""
import logging
from typing import Dict, Any, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages loading and switching between different models for each pipeline step."""
    
    def __init__(self):
        self._loaded_models: Dict[str, Any] = {}
        self._providers: Dict[str, Any] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize provider adapters."""
        # Import providers as needed to avoid circular imports
        try:
            from app.models.ollama_adapter import OllamaAdapter
            self._providers['ollama'] = OllamaAdapter
        except ImportError:
            logger.warning("Ollama adapter not available")
        
        try:
            from app.models.diarizer import PyAnnoteDiarizer, SimpleDiarizer
            self._providers['pyannote'] = PyAnnoteDiarizer
            self._providers['simple'] = SimpleDiarizer
        except ImportError:
            logger.warning("Diarization models not available")
        
        try:
            from app.models.punctuation import PunctuationModel
            self._providers['punctuation'] = PunctuationModel
        except ImportError:
            logger.warning("Punctuation restoration not available")
        
        try:
            from sentence_transformers import SentenceTransformer
            self._providers['sentence_transformers'] = SentenceTransformer
        except ImportError:
            logger.warning("Sentence transformers not available")
        
        # Add additional providers with graceful handling
        try:
            import spacy
            self._providers['spacy'] = spacy.load
        except ImportError:
            logger.warning("spaCy not available")
        
        try:
            from transformers import pipeline
            self._providers['transformers'] = pipeline
        except ImportError:
            logger.warning("Transformers not available")
        
        try:
            import openai
            self._providers['openai'] = openai.OpenAI
        except ImportError:
            logger.warning("OpenAI not available")
    
    def get_model_for_step(self, step: str, **kwargs) -> Any:
        """Get the appropriate model for a specific pipeline step.
        
        Args:
            step: Pipeline step name (e.g., 'summarization', 'diarization')
            **kwargs: Additional arguments for model initialization
            
        Returns:
            Loaded model instance
        """
        model_config = settings.models.get(step)
        if not model_config:
            raise ValueError(f"No model configuration found for step: {step}")
        
        provider = model_config.get('provider')
        model_name = model_config.get('model')
        fallback_model = model_config.get('fallback')
        
        # Create cache key
        cache_key = f"{step}_{provider}_{model_name}"
        
        # Return cached model if available
        if cache_key in self._loaded_models:
            logger.debug(f"Using cached model for {step}: {model_name}")
            return self._loaded_models[cache_key]
        
        # Try to load primary model
        try:
            model = self._load_model(provider, model_name, **kwargs)
            self._loaded_models[cache_key] = model
            logger.info(f"Loaded {provider} model for {step}: {model_name}")
            return model
        except Exception as e:
            logger.warning(f"Failed to load primary model {model_name} for {step}: {e}")
            
            # Try fallback model
            if fallback_model:
                try:
                    fallback_cache_key = f"{step}_{provider}_{fallback_model}"
                    if fallback_cache_key not in self._loaded_models:
                        model = self._load_model(provider, fallback_model, **kwargs)
                        self._loaded_models[fallback_cache_key] = model
                    logger.info(f"Using fallback model for {step}: {fallback_model}")
                    return self._loaded_models[fallback_cache_key]
                except Exception as fallback_e:
                    logger.error(f"Failed to load fallback model {fallback_model}: {fallback_e}")
            
            # If all fails, try rule-based or simple approaches
            return self._get_simple_fallback(step)
    
    def _load_model(self, provider: str, model_name: str, **kwargs) -> Any:
        """Load a specific model with the given provider."""
        if provider == 'ollama':
            return self._providers['ollama'](model_name, **kwargs)
        
        elif provider == 'pyannote':
            return self._providers['pyannote'](model_name, **kwargs)
        
        elif provider == 'simple':
            return self._providers['simple'](**kwargs)
        
        elif provider == 'sentence_transformers':
            return self._providers['sentence_transformers'](model_name, **kwargs)
        
        elif provider == 'local' or provider == 'punctuation':
            return self._providers['punctuation'](model_name, **kwargs)
        
        elif provider == 'spacy':
            if 'spacy' not in self._providers:
                raise ImportError("spaCy not available")
            return self._providers['spacy'](model_name)
        
        elif provider == 'huggingface':
            if 'transformers' not in self._providers:
                raise ImportError("Transformers not available")
            return self._providers['transformers']("text-classification", model=model_name, **kwargs)
        
        elif provider == 'openai':
            if 'openai' not in self._providers:
                raise ImportError("OpenAI not available")
            return self._providers['openai'](api_key=kwargs.get('api_key'))
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _get_simple_fallback(self, step: str) -> Any:
        """Get a simple rule-based fallback for a step."""
        if step == 'diarization':
            from app.models.diarizer import SimpleDiarizer
            return SimpleDiarizer()
        
        elif step == 'punctuation':
            from app.models.punctuation import RuleBasedPunctuation
            return RuleBasedPunctuation()
        
        elif step == 'entity_recognition':
            from app.models.entities import RuleBasedNER
            return RuleBasedNER()
        
        elif step == 'temporal_extraction':
            from app.models.temporal import RuleBasedTemporal
            return RuleBasedTemporal()
        
        else:
            raise ValueError(f"No fallback available for step: {step}")
    
    def update_model_config(self, step: str, provider: str, model: str, fallback: Optional[str] = None):
        """Update model configuration for a step."""
        if step not in settings.models:
            settings.models[step] = {}
        
        settings.models[step]['provider'] = provider
        settings.models[step]['model'] = model
        if fallback:
            settings.models[step]['fallback'] = fallback
        
        # Clear cached models for this step
        keys_to_remove = [k for k in self._loaded_models.keys() if k.startswith(f"{step}_")]
        for key in keys_to_remove:
            del self._loaded_models[key]
        
        logger.info(f"Updated model config for {step}: {provider}/{model}")
    
    def get_available_models(self, step: str) -> Dict[str, list]:
        """Get list of available models for a step."""
        available = {
            'summarization': {
                'ollama': ['llama3.2', 'llama3', 'mistral', 'codellama'],
                'openai': ['gpt-4', 'gpt-3.5-turbo'],
                'huggingface': ['facebook/bart-large-cnn', 't5-base']
            },
            'diarization': {
                'pyannote': ['pyannote/speaker-diarization-3.1', 'pyannote/speaker-diarization'],
                'simple': ['rule_based']
            },
            'punctuation': {
                'local': ['oliverguhr/fullstop-punctuation-multilang-large', 'felflare/bert-restore-punctuation'],
                'rule_based': ['simple']
            },
            'embedding': {
                'sentence_transformers': ['all-mpnet-base-v2', 'all-MiniLM-L6-v2', 'all-distilroberta-v1']
            },
            'entity_recognition': {
                'spacy': ['en_core_web_sm', 'en_core_web_md', 'en_core_web_lg'],
                'huggingface': ['dbmdz/bert-large-cased-finetuned-conll03-english']
            }
        }
        return available.get(step, {})
    
    def health_check(self) -> Dict[str, Dict[str, bool]]:
        """Check health of all configured models."""
        health = {}
        
        for step, config in settings.models.items():
            provider = config.get('provider')
            model = config.get('model')
            
            try:
                # Try to load model
                self.get_model_for_step(step)
                health[step] = {
                    'status': 'healthy',
                    'provider': provider,
                    'model': model,
                    'error': None
                }
            except Exception as e:
                health[step] = {
                    'status': 'unhealthy', 
                    'provider': provider,
                    'model': model,
                    'error': str(e)
                }
        
        return health


# Global model manager instance
model_manager = ModelManager()