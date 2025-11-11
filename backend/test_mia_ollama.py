#!/usr/bin/env python3
"""Test MIA with Ollama using API calls to bypass import issues"""

import json
import requests
from pathlib import Path

class SimpleOllamaExtractor:
    """Simplified Ollama extractor for testing"""
    
    def __init__(self):
        self.url = "http://localhost:11434/api/generate"
        
    def extract_decisions(self, context: str):
        """Extract decisions using Llama 3"""
        
        prompt = f"""You are an expert meeting analyst. Extract DECISIONS from this meeting transcript.

A DECISION is when participants:
- Agree on a course of action ("we decided to...")
- Make a choice between options ("we chose...")
- Approve something ("approved the plan...")
- Conclude or finalize something ("we concluded that...")
- Set policy or direction ("we will...")

EXAMPLES of decisions:
✅ "We decided to push the launch date from October 15th to October 29th"
✅ "We agreed to cut the custom branding feature"
✅ "The team approved moving forward with the security audit"
✅ "We concluded that we need 2-week buffers between phases"
✅ "Let's make October 29th our new launch date"
✅ "We're going with the hybrid approach"

❌ NOT decisions (just discussion):
- "What do you think about the timeline?"
- "We should consider the risks"
- "Let me check with legal"
- "I'm wondering if we should..."

Extract ALL clear decisions from this meeting transcript:

{context}

Return decisions in this EXACT JSON format:
{{
  "decisions": [
    {{
      "decision": "exact decision made (what was decided)",
      "rationale": "why this decision was made (if mentioned)",
      "participants": ["names of people involved in decision"],
      "confidence": 0.9
    }}
  ]
}}

Focus on WHAT was decided, not discussions about what might be decided.
Return ONLY valid JSON, no explanations."""
        
        return self._call_ollama(prompt)
    
    def extract_actions(self, context: str):
        """Extract action items using Llama 3"""
        
        prompt = f"""You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

An ACTION ITEM is a specific task assigned to someone with:
- WHO: Clear owner/assignee
- WHAT: Specific action to take
- WHEN: Due date/deadline (if mentioned)

EXAMPLES of action items:
✅ "Sarah, can you contact the Salesforce account manager by end of day tomorrow?"
   → Owner: Sarah, Action: contact Salesforce account manager, Due: end of day tomorrow

✅ "Marcus will schedule knowledge transfer sessions with James this week"
   → Owner: Marcus, Action: schedule knowledge transfer sessions with James, Due: this week

✅ "Emily needs to update all marketing materials with the new launch date"
   → Owner: Emily, Action: update all marketing materials with new launch date

✅ "I'll coordinate with finance on the security audit budget"
   → Owner: [current speaker], Action: coordinate with finance on security audit budget

OWNERSHIP PATTERNS:
- "John will..." → Owner: John
- "Sarah, can you..." → Owner: Sarah
- "I'll handle..." → Owner: [current speaker]
- "Let's have Marcus..." → Owner: Marcus
- "assigned to Emily" → Owner: Emily

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
        
        return self._call_ollama(prompt)
    
    def extract_risks(self, context: str):
        """Extract risks using Llama 3"""
        
        prompt = f"""You are an expert meeting analyst. Extract RISKS from this meeting transcript.

A RISK is a potential problem, concern, or threat that could impact the project:
- Things that could go wrong
- Blockers or dependencies
- Concerns raised by participants
- Potential failures or delays

EXAMPLES of risks:
✅ "Security audit delay could impact launch timeline"
   → Category: Timeline, Risk: Security audit delay impacting launch

✅ "Key engineer taking paternity leave during launch window"
   → Category: Resource, Risk: Key person dependency during critical period

✅ "Performance issues not resolved before launch"
   → Category: Technical, Risk: Unresolved performance issues

✅ "Budget constraints may require cutting more features"
   → Category: Resource, Risk: Budget overrun forcing feature cuts

✅ "If we can't get Salesforce integration working, enterprise customers won't be happy"
   → Category: Technical, Risk: Salesforce integration affecting enterprise customers

RISK CATEGORIES:
- Timeline: delays, schedule issues, deadline conflicts
- Technical: performance, bugs, integration problems, system issues
- Resource: staffing, budget, capacity, key person dependencies
- Regulatory: compliance, legal issues, audit requirements
- Business: market, customer, competitive, stakeholder concerns

Extract ALL risks from this meeting transcript:

{context}

Return in this EXACT JSON format:
{{
  "risks": [
    {{
      "risk": "clear description of the risk/concern (not a quote)",
      "category": "Timeline/Technical/Resource/Regulatory/Business",
      "mentioned_by": "speaker who raised the concern",
      "confidence": 0.9
    }}
  ]
}}

Focus on POTENTIAL PROBLEMS that could impact the project, not general discussion.
Return ONLY valid JSON, no explanations."""
        
        return self._call_ollama(prompt)
    
    def _call_ollama(self, prompt: str):
        """Call Ollama API"""
        try:
            payload = {
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 1500,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(self.url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Parse JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx + 1]
                    return json.loads(json_str)
                else:
                    return {"error": "No JSON found", "response": response_text}
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}

def main():
    # Load the Q4 Product Launch transcript
    transcript_path = Path("../meeting_transcripts/Q4_Product_Launch_Planning_Meeting_20250315.txt")
    
    if not transcript_path.exists():
        print(f"❌ Transcript not found: {transcript_path}")
        return
    
    with open(transcript_path, "r") as f:
        transcript_content = f.read()
    
    print("🚀 Testing Enhanced MIA with Ollama/Llama 3")
    print("=" * 60)
    print(f"📄 Loaded transcript: {len(transcript_content)} characters")
    
    extractor = SimpleOllamaExtractor()
    
    # Extract decisions
    print("\n🤖 Extracting decisions...")
    print("   This may take 1-2 minutes...")
    decisions_result = extractor.extract_decisions(transcript_content)
    
    if "error" in decisions_result:
        print(f"   ❌ Decision extraction failed: {decisions_result['error']}")
    else:
        decisions = decisions_result.get("decisions", [])
        print(f"\n📋 DECISIONS EXTRACTED: {len(decisions)}")
        for i, decision in enumerate(decisions[:10], 1):
            print(f"  {i}. {decision.get('decision', 'N/A')}")
            if decision.get('rationale'):
                print(f"     💭 Rationale: {decision.get('rationale')}")
            print(f"     👥 Participants: {', '.join(decision.get('participants', []))}")
            print(f"     🎯 Confidence: {decision.get('confidence', 0):.2f}")
            print()
    
    # Extract action items
    print("\n🤖 Extracting action items...")
    actions_result = extractor.extract_actions(transcript_content)
    
    if "error" in actions_result:
        print(f"   ❌ Action extraction failed: {actions_result['error']}")
    else:
        actions = actions_result.get("action_items", [])
        print(f"\n✅ ACTION ITEMS EXTRACTED: {len(actions)}")
        for i, action in enumerate(actions[:15], 1):
            print(f"  {i}. 👤 {action.get('owner', 'N/A')} - {action.get('action', 'N/A')}")
            if action.get('due_date'):
                print(f"     ⏰ Due: {action.get('due_date')}")
            print(f"     🔥 Priority: {action.get('priority', 'N/A')} | Confidence: {action.get('confidence', 0):.2f}")
            print()
    
    # Extract risks  
    print("\n🤖 Extracting risks...")
    risks_result = extractor.extract_risks(transcript_content)
    
    if "error" in risks_result:
        print(f"   ❌ Risk extraction failed: {risks_result['error']}")
    else:
        risks = risks_result.get("risks", [])
        print(f"\n⚠️ RISKS EXTRACTED: {len(risks)}")
        for i, risk in enumerate(risks[:15], 1):
            print(f"  {i}. [{risk.get('category', 'N/A')}] {risk.get('risk', 'N/A')}")
            print(f"     🗣️ Mentioned by: {risk.get('mentioned_by', 'N/A')} | Confidence: {risk.get('confidence', 0):.2f}")
            print()
    
    # Summary
    total_decisions = len(decisions_result.get("decisions", []))
    total_actions = len(actions_result.get("action_items", []))
    total_risks = len(risks_result.get("risks", []))
    
    print(f"\n🎯 COMPARISON TO EXPECTED")
    print("=" * 35)
    print("Expected: 9 decisions, ~20 action items, ~18 risks")
    print(f"Actual:   {total_decisions} decisions, {total_actions} action items, {total_risks} risks")
    
    # Success metrics
    decision_success = total_decisions >= 5  # At least half expected
    action_success = total_actions >= 10 and total_actions <= 30  # Reasonable range
    risk_success = total_risks >= 8 and total_risks <= 25  # Reasonable range
    
    print(f"\n🏆 SUCCESS METRICS")
    print("=" * 20)
    print(f"Decisions: {'✅ GOOD' if decision_success else '❌ POOR'}")
    print(f"Actions:   {'✅ GOOD' if action_success else '❌ POOR'}")
    print(f"Risks:     {'✅ GOOD' if risk_success else '❌ POOR'}")
    
    overall_success = decision_success and action_success and risk_success
    print(f"Overall:   {'🎉 SUCCESS!' if overall_success else '⚠️ NEEDS WORK'}")
    
    # Save results
    results = {
        "decisions": decisions_result.get("decisions", []),
        "action_items": actions_result.get("action_items", []),
        "risks": risks_result.get("risks", []),
        "summary": {
            "total_decisions": total_decisions,
            "total_actions": total_actions,
            "total_risks": total_risks,
            "success_metrics": {
                "decisions": decision_success,
                "actions": action_success,
                "risks": risk_success,
                "overall": overall_success
            }
        }
    }
    
    output_path = Path("ollama_mia_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Full results saved to: {output_path}")

if __name__ == "__main__":
    main()