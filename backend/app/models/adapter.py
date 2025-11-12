"""Model adapter abstraction layer for flexible model inference."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Warning: sentence-transformers import failed: {e}")
    SentenceTransformer = None
import requests
from huggingface_hub import InferenceClient
from app.config.settings import settings


class ModelAdapter(ABC):
    """Abstract base class for model adapters."""
    
    @abstractmethod
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Generate a summary of the input text."""
        pass
    
    @abstractmethod
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        pass
    
    @abstractmethod
    def classify(self, text: str, labels: List[str]) -> Dict[str, Any]:
        """Classify text into one of the given labels."""
        pass
    
    @abstractmethod
    def generate_structured(self, prompt: str, max_length: int = 500) -> str:
        """Generate structured output using a prompt (for JSON extraction, etc.)."""
        pass


class HuggingFaceInferenceAdapter(ModelAdapter):
    """Adapter for Hugging Face Inference API (remote models) using InferenceClient."""
    
    def __init__(self, token: str):
        self.token = token
        # Use the newer InferenceClient which supports more models
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=token
        )
        # Fallback to old API for compatibility
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text using HF Inference API with InferenceClient."""
        # Try the newer InferenceClient first (supports more models)
        try:
            # Note: InferenceClient doesn't support max_length/min_length parameters
            # The model will use its default parameters
            result = self.client.summarization(
                text,
                model=settings.summarization_model
            )
            
            # InferenceClient returns a SummarizationOutput object with summary_text attribute
            if hasattr(result, 'summary_text'):
                summary = result.summary_text
                if summary:
                    return summary
            
            # Fallback: if it's a string
            if isinstance(result, str):
                return result
            
            # Fallback: if it's a dict
            if isinstance(result, dict):
                summary = result.get("summary_text", "")
                if summary:
                    return summary
            
            if result:
                return str(result)
            
        except Exception as inference_err:
            error_msg = str(inference_err)
            error_type = type(inference_err).__name__
            
            # Check if it's a recoverable error (like "index out of range" - input too long)
            if "index out of range" in error_msg.lower() or "bad request" in error_msg.lower():
                # Skip old API fallback for recoverable errors, go straight to local
                raise ValueError(f"InferenceClient error (likely input too long): {error_msg[:200]}") from inference_err
            
            # Fallback to old API endpoint if InferenceClient fails
            try:
                model_url = f"{self.api_url}/{settings.summarization_model}"
                payload = {
                    "inputs": text,
                    "parameters": {
                        "max_length": max_length,
                        "min_length": min_length,
                        "do_sample": False
                    }
                }
                
                response = requests.post(model_url, headers=self.headers, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("summary_text", "")
                elif isinstance(result, dict):
                    return result.get("summary_text", "")
                return ""
                
            except requests.exceptions.HTTPError as http_err:
                if http_err.response.status_code == 410:
                    raise ValueError(
                        f"Model '{settings.summarization_model}' is no longer available (deprecated). "
                        f"Please update SUMMARIZATION_MODEL in your .env file to a supported model or use 'local' strategy"
                    ) from http_err
                elif http_err.response.status_code == 503:
                    raise ValueError(
                        f"Model '{settings.summarization_model}' is currently loading. Please wait a moment and try again."
                    ) from http_err
                else:
                    raise ValueError(
                        f"Error calling HuggingFace API for model '{settings.summarization_model}': {http_err.response.status_code} {http_err.response.reason}"
                    ) from http_err
            except requests.exceptions.RequestException as req_err:
                raise ValueError(f"Network error calling HuggingFace API: {str(req_err)}") from req_err
            except Exception as fallback_err:
                # If both methods fail, raise the original InferenceClient error
                raise ValueError(f"Error using HuggingFace Inference API (InferenceClient: {str(inference_err)}, Fallback: {str(fallback_err)})") from inference_err
        
        # If we get here, InferenceClient returned None or empty
        raise ValueError("InferenceClient returned empty result")
    
    def generate_structured(self, prompt: str, max_length: int = 500) -> str:
        """Generate structured output using text generation (for JSON extraction, etc.)."""
        try:
            # Try using InferenceClient for text generation
            result = self.client.text_generation(
                prompt,
                max_new_tokens=max_length,
                return_full_text=False
            )
            if result:
                return result
        except:
            pass
        
        # Fallback: Use summarization with prompt as input
        # This is a workaround since not all models support text generation
        try:
            # Format prompt as input for summarization
            full_text = prompt + "\n\nProvide a structured response:"
            result = self.summarize(full_text, max_length=max_length, min_length=50)
            return result
        except:
            return ""
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using HF Inference API."""
        model_url = f"{self.api_url}/{settings.ner_model}"
        payload = {"inputs": text}
        
        response = requests.post(model_url, headers=self.headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return []
    
    def classify(self, text: str, labels: List[str]) -> Dict[str, Any]:
        """Classify text using HF Inference API."""
        # Use a zero-shot classification model
        model_url = f"{self.api_url}/facebook/bart-large-mnli"
        payload = {
            "inputs": text,
            "parameters": {"candidate_labels": labels}
        }
        
        response = requests.post(model_url, headers=self.headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, dict):
            return result
        return {"labels": [], "scores": []}


class LocalTransformerAdapter(ModelAdapter):
    """Adapter for local transformer models."""
    
    def __init__(self):
        self._summarizer = None
        self._ner_pipeline = None
        self._classifier = None
        self._embedding_model = None
    
    def _get_summarizer(self):
        """Lazy load summarization model with local caching."""
        if self._summarizer is None:
            # Cache models locally to avoid repeated downloads
            cache_dir = "./models_cache"
            
            # Detect best available device
            import torch
            if torch.cuda.is_available():
                device = 0  # CUDA GPU
                print("[INFO] Using CUDA GPU for summarization")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"  # Apple Silicon GPU
                print("[INFO] Using Apple Silicon (MPS) GPU for summarization")
            else:
                device = -1  # CPU fallback
                print("[INFO] Using CPU for summarization")
            
            model_kwargs = {"cache_dir": cache_dir}
            if device != -1:
                model_kwargs["dtype"] = torch.float16  # Use dtype instead of torch_dtype
            
            self._summarizer = pipeline(
                "summarization",
                model=settings.summarization_model,
                device=device,
                model_kwargs=model_kwargs
            )
        return self._summarizer
    
    def _get_ner_pipeline(self):
        """Lazy load NER pipeline with local caching."""
        if self._ner_pipeline is None:
            cache_dir = "./models_cache"
            
            # Detect best available device
            import torch
            if torch.cuda.is_available():
                device = 0  # CUDA GPU
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"  # Apple Silicon GPU
            else:
                device = -1  # CPU fallback
            
            self._ner_pipeline = pipeline(
                "ner",
                model=settings.ner_model,
                aggregation_strategy="simple",
                device=device,
                model_kwargs={"cache_dir": cache_dir}
            )
        return self._ner_pipeline
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text using local model."""
        summarizer = self._get_summarizer()
        
        # Calculate dynamic max_length based on input length to avoid warnings
        # Rough estimate: 1 token ≈ 4 characters
        input_tokens = len(text) // 4
        # Ensure max_length is reasonable: at least min_length, but not more than input
        dynamic_max_length = max(min_length, min(max_length, max(min_length, input_tokens)))
        dynamic_min_length = min(min_length, dynamic_max_length - 1) if dynamic_max_length > min_length else min_length
        
        # Handle long text by chunking if necessary
        max_input_length = 1024
        if len(text) > max_input_length:
            # Simple chunking strategy
            chunks = [text[i:i+max_input_length] for i in range(0, len(text), max_input_length)]
            summaries = []
            for chunk in chunks:
                chunk_tokens = len(chunk) // 4
                chunk_max = max(min_length, min(100, max(min_length, chunk_tokens)))
                chunk_min = min(min_length, chunk_max - 1) if chunk_max > min_length else min_length
                result = summarizer(chunk, max_length=chunk_max, min_length=chunk_min, do_sample=False)
                summaries.append(result[0]["summary_text"])
            return " ".join(summaries)
        
        result = summarizer(text, max_length=dynamic_max_length, min_length=dynamic_min_length, do_sample=False)
        return result[0]["summary_text"]
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using local NER model."""
        ner_pipeline = self._get_ner_pipeline()
        result = ner_pipeline(text)
        return result if isinstance(result, list) else []
    
    def classify(self, text: str, labels: List[str]) -> Dict[str, Any]:
        """Classify text using local model."""
        # For MVP, use a simple keyword-based classification
        # In production, this would use a fine-tuned classifier
        text_lower = text.lower()
        scores = {}
        for label in labels:
            # Simple keyword matching as fallback
            if label.lower() in text_lower:
                scores[label] = 0.7
            else:
                scores[label] = 0.3 / len(labels)
        
        sorted_labels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "labels": [label for label, _ in sorted_labels],
            "scores": [score for _, score in sorted_labels]
        }
    
    def get_embedding_model(self):
        """Get sentence transformer for embeddings with local caching."""
        if not hasattr(self, '_embedding_model') or self._embedding_model is None:
            cache_dir = "./models_cache"
            # Detect best available device
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = 'mps'  # Apple Silicon GPU
            else:
                device = 'cpu'
            
            if SentenceTransformer is None:
                print("Warning: sentence-transformers not available, skipping embedding model")
                self._embedding_model = None
                return None
            self._embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=cache_dir,
                device=device
            )
        return self._embedding_model
    
    def generate_structured(self, prompt: str, max_length: int = 500) -> str:
        """Generate structured output using text generation."""
        # For local models, we'll use summarization as a workaround
        # since text generation requires specific models
        try:
            # Try to use the summarizer with the prompt
            full_text = prompt + "\n\nProvide a structured response:"
            result = self.summarize(full_text, max_length=max_length, min_length=50)
            return result
        except:
            return ""


class HybridAdapter(ModelAdapter):
    """Hybrid adapter: local models for extraction, HF API for summarization with fallback."""
    
    def __init__(self, token: str):
        self.hf_adapter = HuggingFaceInferenceAdapter(token)
        self.local_adapter = LocalTransformerAdapter()
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Use HF API for summarization, fallback to local if API fails."""
        try:
            return self.hf_adapter.summarize(text, max_length, min_length)
        except (ValueError, requests.exceptions.HTTPError) as e:
            # If HF API fails (model deprecated, network error, etc.), fallback to local
            print(f"Warning: HF API summarization failed: {e}")
            print("Falling back to local summarization model...")
            return self.local_adapter.summarize(text, max_length, min_length)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Use local model for entity extraction (faster, no API calls)."""
        return self.local_adapter.extract_entities(text)
    
    def classify(self, text: str, labels: List[str]) -> Dict[str, Any]:
        """Use local model for classification."""
        return self.local_adapter.classify(text, labels)
    
    def get_embedding_model(self):
        """Get sentence transformer for embeddings with local caching."""
        if not hasattr(self, '_embedding_model') or self._embedding_model is None:
            cache_dir = "./models_cache"
            # Detect best available device
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = 'mps'  # Apple Silicon GPU
            else:
                device = 'cpu'
            
            if SentenceTransformer is None:
                print("Warning: sentence-transformers not available, skipping embedding model")
                self._embedding_model = None
                return None
            self._embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=cache_dir,
                device=device
            )
        return self._embedding_model
    
    def generate_structured(self, prompt: str, max_length: int = 500) -> str:
        """Generate structured output - use HF API first, fallback to local."""
        try:
            return self.hf_adapter.generate_structured(prompt, max_length)
        except:
            return self.local_adapter.generate_structured(prompt, max_length)


def get_model_adapter(strategy: Optional[str] = None) -> ModelAdapter:
    """Factory function to get the appropriate model adapter based on settings."""
    if strategy is None:
        strategy = settings.model_strategy.lower()
    else:
        strategy = strategy.lower()
    
    if strategy == "local":
        return LocalTransformerAdapter()
    elif strategy == "remote":
        if not settings.huggingface_token:
            raise ValueError("HUGGINGFACE_TOKEN is required for remote strategy")
        return HuggingFaceInferenceAdapter(settings.huggingface_token)
    elif strategy == "hybrid":
        if not settings.huggingface_token:
            raise ValueError("HUGGINGFACE_TOKEN is required for hybrid strategy")
        return HybridAdapter(settings.huggingface_token)
    elif strategy == "ollama":
        from app.models.ollama_adapter import OllamaAdapter
        return OllamaAdapter()
    else:
        raise ValueError(f"Unknown model strategy: {strategy}. Available: local, remote, hybrid, ollama")
