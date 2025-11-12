#!/usr/bin/env python3
"""Simple test script to debug action extraction with Ollama"""

import requests
import json

def test_ollama_direct():
    print("🧪 Testing Ollama directly for action extraction")
    
    # Test context with clear action items
    context = """David Chen: Sarah, can you take action on that? I'd like you to reach out to the Salesforce account manager by end of day tomorrow.

Sarah Martinez: Yes, I'll do that. I'll send an email to our account manager, Mike Hendricks, and CC the team.

David Chen: Marcus, I want you to do two things: first, escalate to the internal security team lead, and second, get formal quotes from all three external auditors.

Emily Wilson: I can schedule a three-way meeting with legal and our product team to resolve this."""

    # Action extraction prompt
    action_prompt = f"""You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

An ACTION ITEM is a specific task assigned to someone with:
- WHO: Clear owner/assignee
- WHAT: Specific action to take
- WHEN: Due date/deadline (if mentioned)

EXAMPLES of action items:
✅ "Sarah, can you contact the Salesforce account manager by end of day tomorrow?"
   → Owner: Sarah, Action: contact Salesforce account manager, Due: end of day tomorrow

✅ "Marcus will schedule knowledge transfer sessions with James this week"
   → Owner: Marcus, Action: schedule knowledge transfer sessions with James, Due: this week

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

FOCUS on clear task assignments, not vague discussions.
Return ONLY valid JSON, no explanations."""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": action_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 1500,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            print(f"✅ Raw Ollama response ({len(response_text)} chars):")
            print("=" * 50)
            print(response_text[:1000])
            if len(response_text) > 1000:
                print(f"... (truncated, total {len(response_text)} chars)")
            print("=" * 50)
            
            # Try to parse JSON
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    print("❌ No JSON found in response")
                    return
                
                json_str = response_text[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                
                print(f"✅ Parsed JSON successfully:")
                print(json.dumps(parsed, indent=2))
                
                action_items = parsed.get("action_items", [])
                print(f"\n📋 Found {len(action_items)} action items:")
                for i, action in enumerate(action_items, 1):
                    print(f"  {i}. {action.get('action', 'N/A')}")
                    print(f"     Owner: {action.get('owner', 'N/A')}")
                    print(f"     Due: {action.get('due_date', 'N/A')}")
                    print(f"     Priority: {action.get('priority', 'N/A')}")
                    print()
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Attempted to parse: {json_str[:200]}...")
                
        else:
            print(f"❌ Ollama returned error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error calling Ollama: {e}")

if __name__ == "__main__":
    test_ollama_direct()