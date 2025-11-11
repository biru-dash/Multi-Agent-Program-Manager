#!/usr/bin/env python3
"""Simple test for Ollama adapter without complex dependencies"""

import json
import requests
from pathlib import Path

# Direct Ollama test without import issues
def test_ollama_connection():
    """Test basic Ollama connection"""
    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3",
            "prompt": "Hello, respond with just 'Ollama working!'",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 20}
        }
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Connection error: {e}"

def test_ollama_structured_extraction():
    """Test structured extraction with a simple example"""
    try:
        url = "http://localhost:11434/api/generate"
        
        # Test decision extraction
        prompt = """Extract decisions from this meeting transcript:

"We decided to push the launch date from October 15th to October 29th due to security audit delays. Sarah will update the marketing materials."

Return ONLY this JSON format:
{
  "decisions": [
    {
      "decision": "specific decision made",
      "participants": ["names"],
      "confidence": 0.9
    }
  ]
}"""
        
        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 500}
        }
        
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Try to parse JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                return parsed
            else:
                return {"error": "No JSON found", "response": response_text}
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🚀 Testing Ollama Integration")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("1. Testing Ollama connection...")
    result = test_ollama_connection()
    print(f"   Result: {result}")
    
    if "working" in result.lower():
        print("   ✅ Ollama connection successful!")
        
        # Test 2: Structured extraction
        print("\n2. Testing structured extraction...")
        extraction_result = test_ollama_structured_extraction()
        
        if isinstance(extraction_result, dict) and "decisions" in extraction_result:
            decisions = extraction_result["decisions"]
            print(f"   ✅ Successfully extracted {len(decisions)} decisions!")
            
            for i, decision in enumerate(decisions, 1):
                print(f"   {i}. {decision.get('decision', 'N/A')}")
                print(f"      Participants: {decision.get('participants', [])}")
                print(f"      Confidence: {decision.get('confidence', 0):.2f}")
        else:
            print(f"   ❌ Extraction failed: {extraction_result}")
            
        print("\n🎯 OLLAMA TEST SUMMARY")
        print("=" * 30)
        print("✅ Connection: Working")
        if isinstance(extraction_result, dict) and "decisions" in extraction_result:
            print("✅ JSON Extraction: Working") 
            print("🎉 Ready for full MIA testing!")
        else:
            print("❌ JSON Extraction: Failed")
            print("⚠️  Need to debug structured prompts")
    else:
        print("   ❌ Ollama connection failed!")
        print("   💡 Make sure Ollama is running: ollama serve")
        print("   💡 And Llama 3 is installed: ollama pull llama3")

if __name__ == "__main__":
    main()