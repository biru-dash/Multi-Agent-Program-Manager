#!/usr/bin/env python3
"""Debug action extraction with Ollama"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.adapter import get_model_adapter
from app.preprocessing.parser import TranscriptParser

def test_action_extraction():
    print("🔍 Testing Action Extraction with Ollama")
    print("=" * 50)
    
    # Get Ollama adapter
    try:
        model_adapter = get_model_adapter("ollama")
        print("✅ Ollama adapter loaded")
    except Exception as e:
        print(f"❌ Failed to load Ollama adapter: {e}")
        return
    
    # Test simple action prompt
    test_context = """
David Chen: Sarah, can you take action on that? I'd like you to reach out to the Salesforce account manager by end of day tomorrow.

Sarah Martinez: Yes, I'll do that. I'll send an email to our account manager, Mike Hendricks, and CC the team.

David Chen: Marcus, I want you to do two things: first, escalate to the internal security team lead, and second, get formal quotes from all three external auditors.

Emily Wilson: I can schedule a three-way meeting with legal and our product team to resolve this.
"""

    action_prompt = """You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

An ACTION ITEM is a specific task assigned to someone with:
- WHO: Clear owner/assignee
- WHAT: Specific action to take
- WHEN: Due date/deadline (if mentioned)

Extract ALL action items from this meeting transcript:

{context}

Return in this EXACT JSON format:
{{
  "action_items": [
    {{
      "action": "specific task to be done",
      "owner": "person responsible (use actual names from transcript)",
      "due_date": "deadline if mentioned (or null if not specified)",
      "priority": "high/medium/low based on urgency words",
      "confidence": 0.9
    }}
  ]
}}

Return ONLY valid JSON, no explanations."""

    try:
        print("🤖 Testing Ollama action extraction...")
        print("Context:", test_context[:200] + "...")
        
        response = model_adapter.extract_structured_data(
            action_prompt.format(context=test_context)
        )
        
        print("✅ Ollama response:", response)
        
        action_items = response.get("action_items", [])
        print(f"📋 Found {len(action_items)} action items:")
        
        for i, action in enumerate(action_items, 1):
            print(f"  {i}. {action.get('action', 'N/A')}")
            print(f"     Owner: {action.get('owner', 'N/A')}")
            print(f"     Due: {action.get('due_date', 'N/A')}")
            print(f"     Priority: {action.get('priority', 'N/A')}")
            print(f"     Confidence: {action.get('confidence', 'N/A')}")
            print()
        
    except Exception as e:
        print(f"❌ Ollama extraction failed: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔄 Testing pattern matching fallback...")
        # Test pattern matching
        patterns = [
            r'([A-Za-z]+),?\s+(?:can you|could you|please|will you)\s+([^.!?]+)',
            r'([A-Za-z]+)\s+(?:will|is going to|needs to|should|must)\s+([^.!?]+)',
            r"(?:I'll|I will|I'm going to)\s+([^.!?]+)",
        ]
        
        for pattern_name, pattern in enumerate(patterns, 1):
            import re
            matches = re.finditer(pattern, test_context, re.IGNORECASE)
            print(f"Pattern {pattern_name}: {list(matches)}")

if __name__ == "__main__":
    test_action_extraction()