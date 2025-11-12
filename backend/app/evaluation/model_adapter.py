"""Model adapter for evaluation LLMs supporting multiple providers."""
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from langchain_core.language_models.base import BaseLanguageModel
from langchain_openai import ChatOpenAI
try:
    from langchain_community.llms import Ollama
except ImportError:
    Ollama = None

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EvaluationModelAdapter(ABC):
    """Abstract base class for evaluation model adapters."""
    
    @abstractmethod
    def get_llm(self) -> BaseLanguageModel:
        """Get the configured LLM instance."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model provider is available."""
        pass


class OllamaEvaluationAdapter(EvaluationModelAdapter):
    """Ollama evaluation model adapter."""
    
    def __init__(self, model_name: str = None, base_url: str = None, temperature: float = 0.1):
        self.model_name = model_name or settings.evaluation_model_name
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature
        self._llm = None
        
    def get_llm(self) -> BaseLanguageModel:
        """Get Ollama LLM instance."""
        if self._llm is None:
            if not Ollama:
                raise ImportError("langchain-community is required for Ollama support")
                
            self._llm = Ollama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature
            )
        return self._llm
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                # Check if the model is available
                models = response.json().get("models", [])
                return any(model["name"].startswith(self.model_name) for model in models)
            return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False


class OpenAIEvaluationAdapter(EvaluationModelAdapter):
    """OpenAI evaluation model adapter."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: str = None, temperature: float = 0.1):
        self.model_name = model_name
        self.api_key = api_key or settings.openai_api_key
        self.temperature = temperature
        self._llm = None
        
    def get_llm(self) -> BaseLanguageModel:
        """Get OpenAI LLM instance."""
        if self._llm is None:
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
                
            self._llm = ChatOpenAI(
                model=self.model_name,
                api_key=self.api_key,
                temperature=self.temperature
            )
        return self._llm
    
    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return bool(self.api_key)


class HuggingFaceEvaluationAdapter(EvaluationModelAdapter):
    """HuggingFace evaluation model adapter."""
    
    def __init__(self, model_name: str = None, api_key: str = None, temperature: float = 0.1):
        self.model_name = model_name or settings.evaluation_model_name
        self.api_key = api_key or settings.huggingface_token
        self.temperature = temperature
        self._llm = None
        
    def get_llm(self) -> BaseLanguageModel:
        """Get HuggingFace LLM instance."""
        if self._llm is None:
            try:
                from langchain_community.llms import HuggingFaceHub
                
                if not self.api_key:
                    raise ValueError("HuggingFace API key is required")
                    
                self._llm = HuggingFaceHub(
                    repo_id=self.model_name,
                    huggingfacehub_api_token=self.api_key,
                    model_kwargs={"temperature": self.temperature, "max_length": 2048}
                )
            except ImportError:
                raise ImportError("langchain-community is required for HuggingFace support")
        return self._llm
    
    def is_available(self) -> bool:
        """Check if HuggingFace is available."""
        return bool(self.api_key)


def get_evaluation_model_adapter() -> EvaluationModelAdapter:
    """Get the configured evaluation model adapter."""
    provider = settings.evaluation_model_provider.lower()
    
    if provider == "ollama":
        adapter = OllamaEvaluationAdapter()
        if adapter.is_available():
            logger.info(f"Using Ollama model: {settings.evaluation_model_name}")
            return adapter
        else:
            logger.warning("Ollama not available, falling back...")
            
    elif provider == "openai":
        adapter = OpenAIEvaluationAdapter()
        if adapter.is_available():
            logger.info("Using OpenAI model for evaluation")
            return adapter
        else:
            logger.warning("OpenAI not available, falling back...")
            
    elif provider == "huggingface":
        adapter = HuggingFaceEvaluationAdapter()
        if adapter.is_available():
            logger.info(f"Using HuggingFace model: {settings.evaluation_model_name}")
            return adapter
        else:
            logger.warning("HuggingFace not available, falling back...")
    
    # Fallback logic
    fallback_order = ["ollama", "openai", "huggingface"]
    for fallback_provider in fallback_order:
        if fallback_provider == provider:
            continue  # Skip the already tried provider
            
        try:
            if fallback_provider == "ollama":
                adapter = OllamaEvaluationAdapter(model_name=settings.evaluation_model_fallback)
                if adapter.is_available():
                    logger.info(f"Fallback to Ollama: {settings.evaluation_model_fallback}")
                    return adapter
                    
            elif fallback_provider == "openai" and settings.openai_api_key:
                adapter = OpenAIEvaluationAdapter()
                logger.info("Fallback to OpenAI")
                return adapter
                
            elif fallback_provider == "huggingface" and settings.huggingface_token:
                adapter = HuggingFaceEvaluationAdapter()
                logger.info("Fallback to HuggingFace")
                return adapter
                
        except Exception as e:
            logger.warning(f"Fallback to {fallback_provider} failed: {e}")
            continue
    
    # If all else fails, create a mock adapter that raises an error
    class NoModelAdapter(EvaluationModelAdapter):
        def get_llm(self) -> BaseLanguageModel:
            raise RuntimeError("No evaluation model available. Please configure Ollama, OpenAI, or HuggingFace.")
        
        def is_available(self) -> bool:
            return False
    
    logger.error("No evaluation model providers available")
    return NoModelAdapter()


def get_evaluation_model_info() -> Dict[str, Any]:
    """Get information about the current evaluation model configuration."""
    adapter = get_evaluation_model_adapter()
    
    return {
        "provider": settings.evaluation_model_provider,
        "model_name": settings.evaluation_model_name,
        "fallback_model": settings.evaluation_model_fallback,
        "temperature": settings.evaluation_temperature,
        "available": adapter.is_available(),
        "ollama_url": settings.ollama_base_url,
        "has_openai_key": bool(settings.openai_api_key),
        "has_hf_token": bool(settings.huggingface_token)
    }