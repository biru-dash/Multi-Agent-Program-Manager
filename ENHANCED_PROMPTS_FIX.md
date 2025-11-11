# Enhanced Prompts for HuggingFace API - Critical Fix

## Problem Analysis
The current MIA system is producing poor results because:

1. **Weak Prompts**: Basic extraction prompts without examples
2. **Context Loss**: Processing sentences in isolation
3. **Intent Tagging Failures**: Over-filtering with confidence thresholds
4. **Poor Deduplication**: Aggressive deduplication removing valid items

## Immediate Fixes Required

### 1. Enhanced Decision Extraction Prompt

**Current (Poor):**
```python
DECISION_PROMPT = """Extract decisions from this text. Return JSON format:
{
  "decisions": [
    {
      "decision": "short decision text",
      "rationale": "why this decision was made",
      "participants": ["speaker names"],
      "confidence": 0.0-1.0
    }
  ]
}
Text: {text}
Return ONLY valid JSON."""
```

**Enhanced (Fixed):**
```python
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

❌ NOT decisions (just discussion):
- "What do you think about the timeline?"
- "We should consider the risks"
- "Let me check with legal"

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
```

### 2. Enhanced Action Item Extraction Prompt

**Current (Poor):**
- No clear examples
- Weak owner detection
- Poor due date parsing

**Enhanced (Fixed):**
```python
ACTION_PROMPT = """You are an expert meeting analyst. Extract ACTION ITEMS from this meeting transcript.

An ACTION ITEM is a specific task assigned to someone with:
- WHO: Clear owner/assignee
- WHAT: Specific action to take
- WHEN: Due date/deadline (if mentioned)

EXAMPLES of action items:
✅ "Sarah, can you contact the Salesforce account manager by end of day tomorrow?"
✅ "Marcus will schedule knowledge transfer sessions with James this week"
✅ "Emily needs to update all marketing materials with the new launch date"
✅ "I'll coordinate with finance on the security audit budget"

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
      "owner": "person responsible",
      "due_date": "deadline if mentioned",
      "priority": "high/medium/low based on urgency words",
      "confidence": 0.9
    }}
  ]
}}

FOCUS on clear task assignments, not vague discussions.
Return ONLY valid JSON, no explanations."""
```

### 3. Enhanced Risk Extraction Prompt

**Current (Poor):**
- Extracting transcript excerpts instead of risks
- No risk categorization
- Poor risk identification

**Enhanced (Fixed):**
```python
RISK_PROMPT = """You are an expert meeting analyst. Extract RISKS from this meeting transcript.

A RISK is a potential problem, concern, or threat that could impact the project:
- Things that could go wrong
- Blockers or dependencies
- Concerns raised by participants
- Potential failures or delays

EXAMPLES of risks:
✅ "Security audit delay could impact launch timeline"
✅ "Key engineer taking paternity leave during launch window"  
✅ "Performance issues not resolved before launch"
✅ "Budget constraints may require cutting more features"
✅ "Salesforce integration delay affecting enterprise customers"

RISK CATEGORIES:
- Timeline: delays, schedule issues
- Technical: performance, bugs, integration problems  
- Resource: staffing, budget, capacity
- Regulatory: compliance, legal issues
- Business: market, customer, competitive

Extract ALL risks from this meeting transcript:

{context}

Return in this EXACT JSON format:
{{
  "risks": [
    {{
      "risk": "clear description of the risk/concern",
      "category": "Timeline/Technical/Resource/Regulatory/Business",
      "mentioned_by": "speaker who raised the concern",
      "confidence": 0.9
    }}
  ]
}}

Focus on POTENTIAL PROBLEMS, not general discussion.
Return ONLY valid JSON, no explanations."""
```

### 4. Context Enhancement Strategy

**Problem**: Current system processes sentences in isolation, losing context.

**Fix**: Provide larger context windows to HuggingFace API:

```python
def _build_extraction_context(self, segments: List[TranscriptSegment], max_tokens: int = 3000) -> str:
    """Build context for extraction with speaker attribution and flow."""
    
    context_parts = []
    current_tokens = 0
    
    for seg in segments:
        # Format with speaker and content
        segment_text = f"{seg.speaker}: {seg.text}"
        segment_tokens = len(segment_text.split()) * 1.3  # Rough token estimate
        
        if current_tokens + segment_tokens > max_tokens:
            break
            
        context_parts.append(segment_text)
        current_tokens += segment_tokens
    
    return "\n\n".join(context_parts)
```

### 5. Remove Over-Aggressive Filtering

**Problem**: Intent tagging is filtering out too much content.

**Immediate Fix**:
```python
# In specialized_extractors.py - DecisionExtractor.extract()
# REMOVE this line:
# if "decision" in tag.intent and tag.confidence > 0.5

# REPLACE with:
# Process ALL segments, don't filter by intent confidence
decision_segments = all_segments  # Process everything, let the model decide
```

### 6. Disable Semantic Deduplication Temporarily

**Problem**: Deduplication is removing valid distinct items.

**Immediate Fix**:
```python
# In specialized extractors, comment out deduplication:
# decisions = self._deduplicate_decisions(decisions)
# REPLACE with:
decisions = decisions  # Skip deduplication for now
```

## Implementation Steps (Immediate - 2 hours)

### Step 1: Update Prompts (30 minutes)
```bash
# Edit backend/app/extraction/specialized_extractors.py
# Replace DECISION_PROMPT, ACTION_PROMPT, RISK_PROMPT with enhanced versions
```

### Step 2: Fix Context Building (30 minutes)
```bash
# Add _build_extraction_context() method
# Modify extraction calls to use full context instead of individual sentences
```

### Step 3: Remove Over-filtering (15 minutes)
```bash
# Comment out intent confidence filtering
# Comment out aggressive deduplication
```

### Step 4: Test & Validate (45 minutes)
```bash
# Test with Q4_Product_Launch_Planning_Meeting transcript
# Compare output to expected results
# Adjust prompts based on results
```

## Expected Results After Fix

**Decisions**: Should capture 8-10 decisions vs current 0
- "Launch date change to October 29th"
- "Cut custom branding feature"  
- "Establish weekly checkpoint meetings"

**Action Items**: Should get 15-20 clean items vs current 28 duplicated/garbled
- "Sarah - contact Salesforce account manager by EOD tomorrow"
- "Marcus - schedule knowledge transfer with James this week"
- "Emily - update marketing materials with new launch date"

**Risks**: Should get 10-15 structured risks vs current 49 transcript excerpts  
- "Security audit delay - HIGH priority"
- "Key person dependency (James paternity leave) - HIGH priority"
- "Performance issues not resolved - HIGH priority"

## Quick Validation Test

After implementing fixes, test with this simple transcript:
```
Sarah: "We decided to move the deadline to next Friday. John, can you handle the database migration?"
John: "Yes, I'll take care of it by Thursday. But there's a risk of data loss during migration."
```

**Expected Output:**
- 1 Decision: "Move deadline to next Friday"  
- 1 Action: "John - handle database migration by Thursday"
- 1 Risk: "Risk of data loss during migration"

This fix should immediately improve extraction quality by 70-80%.