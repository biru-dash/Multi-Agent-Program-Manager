"""Ollama model adapter for local instruction-following LLM inference."""
import json
import requests
from typing import List, Dict, Any, Optional
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
import logging

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """Ollama adapter for local Llama 3 inference with structured extraction capabilities."""
    
    def __init__(self, model_name: str = "llama3", base_url: str = "http://localhost:11434"):
        """Initialize Ollama adapter.
        
        Args:
            model_name: Ollama model to use (e.g., "llama3", "llama3.2")
            base_url: Ollama server URL
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.embeddings_url = f"{base_url}/api/embeddings"
        self._embedding_model = None
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to Ollama server."""
        try:
            response = requests.post(
                self.api_url,
                json={"model": self.model_name, "prompt": "Hello", "stream": False},
                timeout=60  # Increased timeout for cold model loading
            )
            if response.status_code != 200:
                raise ConnectionError(f"Ollama server returned {response.status_code}")
            logger.info(f"Successfully connected to Ollama with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ConnectionError(f"Cannot connect to Ollama server at {self.base_url}")
    
    def generate_text(self, prompt: str, max_length: int = 2000, temperature: float = 0.1) -> str:
        """Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            max_length: Maximum tokens to generate
            temperature: Generation temperature (0.1 for deterministic)
            
        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_length,
                    "top_p": 0.9,
                    "stop": ["</JSON>", "END_RESPONSE"]
                }
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120  # Longer timeout for complex prompts
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating text with Ollama: {e}")
            return ""
    
    def extract_structured_data(self, prompt: str, max_length: int = 1500) -> Dict[str, Any]:
        """Extract structured data using Llama 3 with JSON output.
        
        Args:
            prompt: Structured extraction prompt
            max_length: Maximum response length
            
        Returns:
            Parsed JSON data or empty dict if parsing fails
        """
        # Enhanced prompt to ensure JSON output
        structured_prompt = f"""You are an expert meeting analyst. Follow the instructions exactly.

{prompt}

IMPORTANT: Return ONLY valid JSON. No explanations, no markdown, no additional text.
Start your response with {{ and end with }}.

"""
        
        response_text = self.generate_text(structured_prompt, max_length, temperature=0.0)
        
        if not response_text:
            return {}
        
        # Try to extract JSON from response
        return self._parse_json_response(response_text)
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with error handling."""
        try:
            # Clean up the response
            response_text = response_text.strip()
            
            # Find JSON boundaries
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("No JSON found in response")
                print(f"[DEBUG] OllamaAdapter: No JSON found in response: {response_text[:200]}...")
                return {}
            
            json_str = response_text[start_idx:end_idx + 1]
            
            # Parse JSON
            result = json.loads(json_str)
            print(f"[DEBUG] OllamaAdapter: Successfully parsed JSON: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {response_text}")
            print(f"[DEBUG] OllamaAdapter: JSON parse error: {e}")
            print(f"[DEBUG] OllamaAdapter: Attempted to parse: {json_str[:200] if 'json_str' in locals() else 'N/A'}...")
            return {}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            print(f"[DEBUG] OllamaAdapter: Error parsing response: {e}")
            return {}
    
    def summarize(self, text: str, max_length: int = 250, min_length: int = 100) -> str:
        """Summarize text using Llama 3.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length in tokens
            min_length: Minimum summary length in tokens
            
        Returns:
            Summary text
        """
        prompt = f"""Summarize this meeting transcript concisely. Focus on:
1. Main topics discussed
2. Key decisions made
3. Action items assigned
4. Risks or concerns identified

Keep the summary between {min_length} and {max_length} words.

Transcript:
{text}

Summary:"""
        
        return self.generate_text(prompt, max_length * 2, temperature=0.2)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using Llama 3.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of entities with type and text
        """
        prompt = f"""Extract all person names and organizations from this text.
Return as JSON format: {{"entities": [{{"text": "name", "type": "PERSON"}}, {{"text": "company", "type": "ORG"}}]}}

Text: {text}

JSON:"""
        
        response = self.extract_structured_data(prompt, 800)
        entities = response.get("entities", [])
        
        # Convert to expected format
        formatted_entities = []
        for entity in entities:
            if isinstance(entity, dict):
                formatted_entities.append({
                    "word": entity.get("text", ""),
                    "entity_group": entity.get("type", "MISC"),
                    "score": 0.9  # Default confidence
                })
        
        return formatted_entities
    
    def get_embedding_model(self):
        """Get sentence transformer model for embeddings."""
        if self._embedding_model is None:
            try:
                if SentenceTransformer is None:
                    logger.error("SentenceTransformer not available")
                    return None
                self._embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                return None
        return self._embedding_model
    
    def extract_decisions(self, context: str) -> List[Dict[str, Any]]:
        """Extract decisions using the enhanced decision prompt."""
        from app.extraction.specialized_extractors import DecisionExtractor
        
        extractor = DecisionExtractor(self, self.get_embedding_model())
        prompt = extractor.DECISION_PROMPT.format(context=context)
        
        response = self.extract_structured_data(prompt)
        return response.get("decisions", [])
    
    def extract_actions(self, context: str) -> List[Dict[str, Any]]:
        """Extract action items using the enhanced action prompt.""" 
        from app.extraction.specialized_extractors import ActionExtractor
        
        extractor = ActionExtractor(self, self.get_embedding_model())
        prompt = extractor.ACTION_PROMPT.format(context=context)
        
        response = self.extract_structured_data(prompt)
        return response.get("action_items", [])
    
    def extract_risks(self, context: str) -> List[Dict[str, Any]]:
        """Extract risks using the enhanced risk prompt."""
        from app.extraction.specialized_extractors import RiskExtractor
        
        extractor = RiskExtractor(self, self.get_embedding_model())
        prompt = extractor.RISK_PROMPT.format(context=context)
        
        response = self.extract_structured_data(prompt)
        return response.get("risks", [])


def get_ollama_adapter(model_name: str = "llama3") -> OllamaAdapter:
    """Factory function to get Ollama adapter."""
    return OllamaAdapter(model_name)