"""Model adapter abstraction layer for flexible model inference."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import requests
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


class HuggingFaceInferenceAdapter(ModelAdapter):
    """Adapter for Hugging Face Inference API (remote models)."""
    
    def __init__(self, token: str):
        self.token = token
        self.api_url = "https://api-inference.huggingface.co/models"
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text using HF Inference API."""
        model_url = f"{self.api_url}/{settings.summarization_model}"
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": max_length,
                "min_length": min_length,
                "do_sample": False
            }
        }
        
        response = requests.post(model_url, headers=self.headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("summary_text", "")
        elif isinstance(result, dict):
            return result.get("summary_text", "")
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
            self._summarizer = pipeline(
                "summarization",
                model=settings.summarization_model,
                device=-1,  # Use CPU (set to 0 for GPU if available)
                model_kwargs={"cache_dir": cache_dir}
            )
        return self._summarizer
    
    def _get_ner_pipeline(self):
        """Lazy load NER pipeline with local caching."""
        if self._ner_pipeline is None:
            cache_dir = "./models_cache"
            self._ner_pipeline = pipeline(
                "ner",
                model=settings.ner_model,
                aggregation_strategy="simple",
                device=-1,  # Use CPU
                model_kwargs={"cache_dir": cache_dir}
            )
        return self._ner_pipeline
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text using local model."""
        summarizer = self._get_summarizer()
        
        # Handle long text by chunking if necessary
        max_input_length = 1024
        if len(text) > max_input_length:
            # Simple chunking strategy
            chunks = [text[i:i+max_input_length] for i in range(0, len(text), max_input_length)]
            summaries = []
            for chunk in chunks:
                result = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
                summaries.append(result[0]["summary_text"])
            return " ".join(summaries)
        
        result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
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


class HybridAdapter(ModelAdapter):
    """Hybrid adapter: local models for extraction, HF API for summarization."""
    
    def __init__(self, token: str):
        self.hf_adapter = HuggingFaceInferenceAdapter(token)
        self.local_adapter = LocalTransformerAdapter()
    
    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Use HF API for summarization (more powerful models)."""
        return self.hf_adapter.summarize(text, max_length, min_length)
    
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
            self._embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=cache_dir
            )
        return self._embedding_model


def get_model_adapter() -> ModelAdapter:
    """Factory function to get the appropriate model adapter based on settings."""
    strategy = settings.model_strategy.lower()
    
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
    else:
        raise ValueError(f"Unknown model strategy: {strategy}")
