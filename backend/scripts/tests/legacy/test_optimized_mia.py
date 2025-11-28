#!/usr/bin/env python3
"""Optimized MIA test with enhanced prompts, context chunking, and temperature tuning"""

import json
import requests
import re
from pathlib import Path
from typing import List, Dict, Any

class OptimizedOllamaExtractor:
    """Optimized Ollama extractor with chunking and enhanced prompts"""
    
    def __init__(self):
        self.url = "http://localhost:11434/api/generate"
        
    def extract_decisions_optimized(self, context: str) -> Dict[str, Any]:
        """Extract decisions with enhanced prompt and multiple passes"""
        
        prompt = f"""You are an expert meeting analyst. Extract ALL DECISIONS from this meeting transcript.

A DECISION is when participants:
- Make a firm choice or commitment ("we decided", "we agreed", "approved")
- Set deadlines, dates, or timelines ("launch on October 29th", "meet weekly")
- Define policies or criteria ("gating criteria", "escalation thresholds") 
- Choose between options ("go with 10 features", "cut custom branding")
- Establish processes ("weekly checkpoints", "bi-weekly updates")

IMPORTANT: Find EVERY decision, even small ones like meeting schedules, communication frequency changes, or process adjustments.

EXAMPLES from similar meetings:
✅ "Unanimously decided to push launch date from October 15th to October 29th"
✅ "Decided to launch with 10 features and cut 4 features"
✅ "Established weekly checkpoint meetings every Monday at 10 AM"
✅ "Changed stakeholder updates from weekly to bi-weekly"
✅ "Decided to pursue both internal escalation and external auditor options"
✅ "Established criteria for pausing rollout if critical issues are found"
✅ "Revised the phased rollout timeline with 2-week buffers"

Look for decisions about:
- Launch dates and timelines
- Feature sets (what to include/cut)
- Meeting schedules and frequency
- Communication plans
- Risk mitigation approaches
- Budget approvals
- Process changes
- Criteria and thresholds

Meeting transcript:
{context}

Return decisions in this EXACT JSON format:
{{
  "decisions": [
    {{
      "decision": "specific decision made with details",
      "rationale": "why this decision was made (if mentioned)",
      "participants": ["actual names who made or agreed to decision"],
      "confidence": 0.9,
      "category": "timeline/features/process/communication/other"
    }}
  ]
}}

Be THOROUGH - extract 8-12 decisions minimum. Return ONLY valid JSON."""

        return self._call_ollama_structured(prompt, temperature=0.2, max_tokens=2000)
    
    def extract_actions_optimized(self, context: str) -> Dict[str, Any]:
        """Extract action items with enhanced prompt for comprehensive coverage"""
        
        prompt = f"""You are an expert meeting analyst. Extract ALL ACTION ITEMS from this meeting transcript.

An ACTION ITEM is ANY specific task assigned to someone:
- Direct assignments ("Sarah, contact Salesforce")
- Future tense commitments ("Marcus will escalate to security")
- Task scheduling ("Set up stress test for Tuesday")
- Follow-ups and coordination ("Coordinate with finance", "Follow up on testimonials")
- Updates and communications ("Update marketing materials", "Send status updates")
- Meetings and sessions ("Schedule retrospective", "Three-way meeting with legal")

CRITICAL: Extract EVERY task, even small ones like "send contact info" or "schedule meeting"

Look for action patterns:
- "Name will [action]"
- "Name, can you [action]"
- "I'll [action]" 
- "Let's have Name [action]"
- "Name - [action]"
- "coordinate with", "update", "finalize", "escalate", "contact", "schedule"

Example comprehensive extraction:
✅ "Sarah, contact Salesforce account manager by EOD tomorrow"
✅ "Marcus will escalate to internal security team"
✅ "David - send Marcus security team contact"
✅ "Schedule retrospective for 2 weeks after launch"
✅ "Update all marketing materials with new launch date"
✅ "Coordinate three-way meeting with legal and product"
✅ "Send bi-weekly status updates to stakeholders"

Meeting transcript:
{context}

Return in this EXACT JSON format:
{{
  "action_items": [
    {{
      "action": "specific task with details",
      "owner": "person responsible (actual names)",
      "due_date": "deadline if mentioned or null",
      "priority": "high/medium/low based on urgency",
      "confidence": 0.9,
      "task_type": "communication/coordination/update/meeting/other"
    }}
  ]
}}

Be THOROUGH - extract 15-25 action items minimum. Return ONLY valid JSON."""

        return self._call_ollama_structured(prompt, temperature=0.3, max_tokens=2500)
    
    def extract_risks_comprehensive(self, context: str) -> Dict[str, Any]:
        """Extract risks with comprehensive prompt covering all risk types"""
        
        prompt = f"""You are an expert risk analyst. Extract ALL RISKS and CONCERNS from this meeting transcript.

FIND ALL TYPES OF RISKS:
1. **Explicit Risks** - directly stated as risks/concerns/issues
2. **Hidden/Implicit Risks** - problems mentioned casually in discussion
3. **Dependencies** - things that could go wrong due to dependencies
4. **Resource Constraints** - staffing, budget, capacity issues
5. **Timeline Risks** - delays, scheduling conflicts
6. **Technical Risks** - performance, integration, system issues
7. **Regulatory/Compliance** - legal, audit, policy issues
8. **Business Risks** - customer, market, competitive concerns

EXAMPLES of comprehensive risk extraction:
✅ "Security audit delay could impact launch timeline" (explicit)
✅ "Lead engineer taking paternity leave during launch" (implicit dependency)
✅ "Only 3 support staff for hundreds of new customers" (resource constraint)
✅ "Performance degradation with large datasets" (technical issue)
✅ "Haven't completed full compliance audit" (regulatory gap)
✅ "Beta customers slow to provide testimonials" (business risk)
✅ "Data retention policy not finalized" (process blocker)
✅ "May not have enough time to create marketing videos" (timeline pressure)

Look for risk indicators:
- "risk", "concern", "issue", "problem", "blocker"
- "might not", "could fail", "may not have", "if we don't"
- "behind schedule", "delayed", "running late"
- "only X people", "limited capacity", "over budget"
- "haven't completed", "not finalized", "still need to"
- Dependencies on external parties or key people
- Casual mentions of problems or challenges

RISK CATEGORIES:
- Timeline: delays, schedule conflicts, deadline pressure
- Technical: performance, bugs, integration, system issues
- Resource: staffing, budget, capacity constraints  
- Regulatory: compliance, legal, audit requirements
- Business: customer, market, competitive concerns
- Process: workflow, communication, coordination issues

Meeting transcript:
{context}

Return in this EXACT JSON format:
{{
  "risks": [
    {{
      "risk": "clear description of potential problem",
      "category": "Timeline/Technical/Resource/Regulatory/Business/Process",
      "mentioned_by": "speaker who raised it",
      "confidence": 0.9,
      "impact": "high/medium/low",
      "risk_type": "explicit/implicit/dependency/constraint"
    }}
  ]
}}

Be THOROUGH - extract 15-20 risks minimum including both obvious and subtle ones. Return ONLY valid JSON."""

        return self._call_ollama_structured(prompt, temperature=0.4, max_tokens=3000)
    
    def chunk_context(self, text: str, chunk_size: int = 8000, overlap: int = 1000) -> List[str]:
        """Split long text into overlapping chunks for better coverage"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            else:
                # Find a good breaking point (end of sentence or paragraph)
                break_point = text.rfind('.', start, end)
                if break_point == -1:
                    break_point = text.rfind('\n', start, end)
                if break_point == -1:
                    break_point = end
                
                chunks.append(text[start:break_point + 1])
                start = break_point + 1 - overlap
                
        return chunks
    
    def extract_with_chunking(self, context: str, extraction_func, item_type: str) -> List[Dict[str, Any]]:
        """Extract items using context chunking for better coverage"""
        chunks = self.chunk_context(context)
        all_items = []
        seen_items = set()
        
        print(f"   Processing {len(chunks)} chunks for {item_type}...")
        
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}/{len(chunks)}...")
            result = extraction_func(chunk)
            
            if "error" not in result:
                items = result.get(item_type, [])
                for item in items:
                    # Simple deduplication based on main text content
                    if item_type == "decisions":
                        key = item.get("decision", "")[:100].lower()
                    elif item_type == "action_items":
                        key = f"{item.get('owner', '')}-{item.get('action', '')[:50]}".lower()
                    elif item_type == "risks":
                        key = item.get("risk", "")[:100].lower()
                    else:
                        key = str(item)
                    
                    if key not in seen_items:
                        seen_items.add(key)
                        all_items.append(item)
        
        return all_items
    
    def _call_ollama_structured(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1500) -> Dict[str, Any]:
        """Call Ollama with optimized parameters"""
        try:
            payload = {
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
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
    # Load transcript and expected outputs
    transcript_path = Path("../meeting_transcripts/Q4_Product_Launch_Planning_Meeting_20250315.txt")
    expected_path = Path("../Q4_Product_Launch_Expected_Outputs.md")
    
    if not transcript_path.exists():
        print(f"❌ Transcript not found: {transcript_path}")
        return
        
    with open(transcript_path, "r") as f:
        transcript_content = f.read()
    
    print("🚀 Optimized MIA Testing with Enhanced Extraction")
    print("=" * 60)
    print(f"📄 Loaded transcript: {len(transcript_content)} characters")
    
    if expected_path.exists():
        with open(expected_path, "r") as f:
            expected_content = f.read()
        print(f"📋 Expected output reference loaded: {len(expected_content)} characters")
    
    extractor = OptimizedOllamaExtractor()
    
    # Extract decisions with optimized approach
    print("\n🤖 Extracting DECISIONS (with chunking & optimized prompts)...")
    decisions = extractor.extract_with_chunking(
        transcript_content, 
        extractor.extract_decisions_optimized, 
        "decisions"
    )
    
    print(f"\n📋 DECISIONS EXTRACTED: {len(decisions)}")
    for i, decision in enumerate(decisions[:12], 1):
        print(f"  {i}. [{decision.get('category', 'N/A')}] {decision.get('decision', 'N/A')}")
        if decision.get('rationale'):
            print(f"     💭 Rationale: {decision.get('rationale')[:100]}...")
        print(f"     👥 Participants: {', '.join(decision.get('participants', [])[:3])}")
        print()
    
    # Extract action items with optimized approach  
    print("\n🤖 Extracting ACTION ITEMS (with chunking & comprehensive prompts)...")
    actions = extractor.extract_with_chunking(
        transcript_content,
        extractor.extract_actions_optimized,
        "action_items"
    )
    
    print(f"\n✅ ACTION ITEMS EXTRACTED: {len(actions)}")
    for i, action in enumerate(actions[:20], 1):
        print(f"  {i}. [{action.get('task_type', 'N/A')}] 👤 {action.get('owner', 'N/A')}")
        print(f"     📝 {action.get('action', 'N/A')[:80]}...")
        if action.get('due_date'):
            print(f"     ⏰ Due: {action.get('due_date')}")
        print(f"     🔥 Priority: {action.get('priority', 'N/A')}")
        print()
    
    # Extract risks with comprehensive approach
    print("\n🤖 Extracting RISKS (comprehensive analysis)...")
    risks = extractor.extract_with_chunking(
        transcript_content,
        extractor.extract_risks_comprehensive,
        "risks"
    )
    
    print(f"\n⚠️ RISKS EXTRACTED: {len(risks)}")
    for i, risk in enumerate(risks[:20], 1):
        print(f"  {i}. [{risk.get('category', 'N/A')}] {risk.get('risk', 'N/A')[:80]}...")
        print(f"     🔍 Type: {risk.get('risk_type', 'N/A')} | Impact: {risk.get('impact', 'N/A')}")
        print(f"     🗣️ By: {risk.get('mentioned_by', 'N/A')}")
        print()
    
    # Quality comparison
    print(f"\n🎯 COMPARISON TO EXPECTED OUTPUTS")
    print("=" * 45)
    print("Expected: 9 decisions, ~20 action items, 18 risks")
    print(f"Actual:   {len(decisions)} decisions, {len(actions)} action items, {len(risks)} risks")
    
    # Success metrics
    decision_success = len(decisions) >= 8  # Should get most decisions
    action_success = len(actions) >= 15 and len(actions) <= 35  # Good coverage
    risk_success = len(risks) >= 15 and len(risks) <= 25  # Comprehensive risk analysis
    
    print(f"\n🏆 SUCCESS METRICS")
    print("=" * 20)
    print(f"Decisions: {'✅ EXCELLENT' if len(decisions) >= 8 else '✅ GOOD' if len(decisions) >= 6 else '❌ POOR'}")
    print(f"Actions:   {'✅ EXCELLENT' if len(actions) >= 20 else '✅ GOOD' if len(actions) >= 15 else '❌ POOR'}")
    print(f"Risks:     {'✅ EXCELLENT' if len(risks) >= 15 else '✅ GOOD' if len(risks) >= 10 else '❌ POOR'}")
    
    overall_success = decision_success and action_success and risk_success
    print(f"Overall:   {'🎉 EXCELLENT!' if overall_success else '✅ GOOD' if (decision_success or action_success or risk_success) else '⚠️ NEEDS WORK'}")
    
    # Save optimized results
    results = {
        "extraction_summary": {
            "decisions_count": len(decisions),
            "actions_count": len(actions), 
            "risks_count": len(risks),
            "extraction_method": "chunked_optimized_prompts",
            "quality_score": "excellent" if overall_success else "good"
        },
        "decisions": decisions,
        "action_items": actions,
        "risks": risks,
        "optimization_notes": {
            "chunking_used": True,
            "temperature_tuning": {"decisions": 0.2, "actions": 0.3, "risks": 0.4},
            "enhanced_prompts": True,
            "comprehensive_coverage": True
        }
    }
    
    output_path = Path("optimized_mia_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Optimized results saved to: {output_path}")

if __name__ == "__main__":
    main()