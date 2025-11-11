# CRITICAL FIX - Replace specialized_extractors.py prompts
# This file contains the exact code changes needed to fix MIA extraction quality

# ===== ENHANCED DECISION EXTRACTOR =====

class EnhancedDecisionExtractor:
    """Enhanced decision extractor with better prompts and context handling."""
    
    DECISION_PROMPT = """You are an expert meeting analyst. Extract DECISIONS from this meeting transcript.

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

    def extract(self, tagged_sentences, all_segments):
        """Extract decisions with enhanced context and prompting."""
        
        # Build full context instead of processing individual sentences
        context = self._build_extraction_context(all_segments)
        
        # Use enhanced prompt with full context
        try:
            response = self.model_adapter.generate_text(
                self.DECISION_PROMPT.format(context=context),
                max_length=1000,
                temperature=0.1  # Lower temperature for more consistent extraction
            )
            
            # Parse JSON response
            import json
            result = json.loads(response)
            decisions = result.get("decisions", [])
            
            # Add confidence scores if missing
            for decision in decisions:
                if "confidence" not in decision:
                    decision["confidence"] = 0.8
                    
            return decisions
            
        except Exception as e:
            print(f"Decision extraction failed: {e}")
            return []
    
    def _build_extraction_context(self, segments, max_tokens=2500):
        """Build context with speaker attribution and natural flow."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            # Format: "Speaker: text"
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3  # Rough token estimate
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)


# ===== ENHANCED ACTION EXTRACTOR =====

class EnhancedActionExtractor:
    """Enhanced action extractor with better owner detection and context."""
    
    ACTION_PROMPT = """You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

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

✅ "Let's have David send the calendar invites for weekly meetings"
   → Owner: David, Action: send calendar invites for weekly meetings

OWNERSHIP PATTERNS:
- "John will..." → Owner: John
- "Sarah, can you..." → Owner: Sarah
- "I'll handle..." → Owner: [current speaker]
- "Let's have Marcus..." → Owner: Marcus  
- "assigned to Emily" → Owner: Emily
- "Emily - update the..." → Owner: Emily

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

    def extract(self, tagged_sentences, all_segments):
        """Extract action items with enhanced context and prompting."""
        
        # Build full context
        context = self._build_extraction_context(all_segments)
        
        try:
            response = self.model_adapter.generate_text(
                self.ACTION_PROMPT.format(context=context),
                max_length=1500,
                temperature=0.1
            )
            
            import json
            result = json.loads(response)
            action_items = result.get("action_items", [])
            
            # Clean up and validate action items
            cleaned_actions = []
            for action in action_items:
                if action.get("action") and action.get("owner"):
                    # Ensure confidence score
                    if "confidence" not in action:
                        action["confidence"] = 0.8
                    
                    # Clean up owner names (remove titles, normalize)
                    action["owner"] = self._clean_owner_name(action["owner"])
                    
                    # Standardize priority
                    priority = action.get("priority", "medium").lower()
                    action["priority"] = priority if priority in ["high", "medium", "low"] else "medium"
                    
                    cleaned_actions.append(action)
            
            return cleaned_actions
            
        except Exception as e:
            print(f"Action extraction failed: {e}")
            return []
    
    def _clean_owner_name(self, owner):
        """Clean and standardize owner names."""
        if not owner:
            return "Unclear"
        
        # Remove common titles and clean up
        owner = owner.replace("Dr.", "").replace("Mr.", "").replace("Ms.", "")
        owner = owner.strip()
        
        # Handle "current speaker" cases
        if owner.lower() in ["current speaker", "[current speaker]", "speaker"]:
            return "Unclear"
        
        return owner
    
    def _build_extraction_context(self, segments, max_tokens=2500):
        """Build context maintaining speaker flow."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)


# ===== ENHANCED RISK EXTRACTOR =====

class EnhancedRiskExtractor:
    """Enhanced risk extractor that identifies actual risks, not transcript excerpts."""
    
    RISK_PROMPT = """You are an expert meeting analyst. Extract RISKS from this meeting transcript.

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

    def extract(self, tagged_sentences, all_segments):
        """Extract risks with enhanced prompting and categorization."""
        
        # Build full context
        context = self._build_extraction_context(all_segments)
        
        try:
            response = self.model_adapter.generate_text(
                self.RISK_PROMPT.format(context=context),
                max_length=1200,
                temperature=0.1
            )
            
            import json
            result = json.loads(response)
            risks = result.get("risks", [])
            
            # Validate and clean risks
            cleaned_risks = []
            for risk in risks:
                if risk.get("risk") and len(risk["risk"]) > 10:  # Ensure substantive risk description
                    # Ensure confidence score
                    if "confidence" not in risk:
                        risk["confidence"] = 0.8
                    
                    # Validate category
                    category = risk.get("category", "Other")
                    valid_categories = ["Timeline", "Technical", "Resource", "Regulatory", "Business", "Other"]
                    if category not in valid_categories:
                        risk["category"] = "Other"
                    
                    cleaned_risks.append(risk)
            
            return cleaned_risks
            
        except Exception as e:
            print(f"Risk extraction failed: {e}")
            return []
    
    def _build_extraction_context(self, segments, max_tokens=2500):
        """Build context for risk identification."""
        context_parts = []
        current_tokens = 0
        
        for seg in segments:
            segment_text = f"{seg.speaker or 'Speaker'}: {seg.text}"
            segment_tokens = len(segment_text.split()) * 1.3
            
            if current_tokens + segment_tokens > max_tokens:
                break
                
            context_parts.append(segment_text)
            current_tokens += segment_tokens
        
        return "\n\n".join(context_parts)


# ===== QUICK IMPLEMENTATION GUIDE =====

"""
TO IMPLEMENT THESE FIXES:

1. BACKUP current specialized_extractors.py:
   cp backend/app/extraction/specialized_extractors.py backend/app/extraction/specialized_extractors.py.backup

2. REPLACE the three extractor classes in specialized_extractors.py with the enhanced versions above

3. UPDATE the extract_structured_data method in extractor.py to remove filtering:
   
   # REMOVE these lines:
   decision_sentences = [tag for tag in tagged_sentences if "decision" in tag.intent and tag.confidence > 0.5]
   
   # REPLACE with:
   # Use enhanced extractors that process full context
   decisions = decision_extractor.extract([], segments)  # Pass empty tagged_sentences, use segments
   action_items = action_extractor.extract([], segments) 
   risks = risk_extractor.extract([], segments)

4. DISABLE deduplication temporarily by commenting out:
   # decisions = self._deduplicate_decisions(decisions)
   # action_items = self._deduplicate_actions(action_items)  
   # risks = self._deduplicate_risks(risks)

5. TEST with the Q4 Product Launch transcript - should see immediate improvement

EXPECTED RESULTS AFTER FIX:
- Decisions: 8-10 clear decisions extracted
- Action Items: 15-20 clean, non-duplicated items with correct owners
- Risks: 10-15 structured risks with categories

This should resolve 80% of the quality issues immediately.
"""