# Extraction Improvements - Specialized Modules with Intent Tagging

## Overview
This document outlines the comprehensive improvements made to action items, decisions, and risks extraction using a specialized modular architecture with intent tagging.

## Key Improvements

### 1. Specialized Extractor Modules ✅

**Location:** `backend/app/extraction/specialized_extractors.py`

Created three specialized extractor classes:

#### DecisionExtractor
- Focused on extracting key decisions (agreements, approvals, finalizations)
- Extracts participants, rationale, and confidence
- Uses semantic deduplication to merge similar decisions

#### ActionExtractor
- Specialized for action items with owner, action, due date, priority
- Advanced owner detection using NER and pattern matching
- Merges related actions by the same owner
- Better due date extraction with multiple patterns

#### RiskExtractor
- Categorizes risks into: Timeline, Resource, Data, Process, Technical, Other
- Identifies who mentioned the risk
- Semantic deduplication of similar risks

### 2. Intent Tagging System ✅

**Location:** `backend/app/extraction/specialized_extractors.py` - `IntentTagger` class

#### How It Works
1. **Pre-computes embeddings** for canonical intent examples:
   - "decision": "we decided", "we agreed", "approved"
   - "action": "john will handle", "i will send", "assigned to"
   - "risk": "there's a risk", "we're concerned", "blocker"
   - "discussion": "what do you think", "let's discuss"

2. **Tags each sentence** with semantic intents using cosine similarity
3. **Filters sentences** by intent before extraction (confidence > 0.6)
4. **Falls back** to keyword-based tagging if embeddings unavailable

#### Benefits
- **Semantic filtering**: Only processes relevant sentences for each extractor
- **Better accuracy**: Intent-based filtering reduces false positives
- **Modular design**: Each extractor only sees relevant sentences

### 3. Enhanced Preprocessing ✅

**Location:** `backend/app/preprocessing/cleaner.py`

#### New Preprocessing Steps

1. **Remove Small Talk**
   - Removes greetings: "hi", "hello", "good morning"
   - Removes acknowledgments: "thanks", "okay", "sure", "got it"
   - Filters single-word acknowledgments: "yeah", "yep", "ok"

2. **Merge Short Turns**
   - Merges consecutive segments from same speaker if < 10 words
   - Reduces fragmentation of action items

3. **Remove Repetitions**
   - Removes immediate word repetitions: "yeah yeah" → "yeah"
   - Removes triple repetitions: "exactly exactly exactly" → "exactly"

4. **Enhanced Filler Removal**
   - Now includes repetition removal in cleaning pipeline

#### Processing Order
1. Remove small talk
2. Merge short turns
3. Remove fillers and repetitions
4. Normalize speakers
5. Segment by topics (optional)

### 4. Post-Processing Improvements ✅

Each specialized extractor includes:

#### Deduplication
- **Semantic similarity**: Uses embeddings to find similar items
- **Similarity threshold**: 0.8 for decisions/risks, 0.75 for actions
- **Merging logic**: Combines similar items, keeps highest confidence

#### Confidence Filtering
- **Minimum confidence**: 0.5 (filtered in main extractor)
- **Confidence boost**: +0.1 for explicit keywords
- **Confidence reduction**: -0.1 if owner unclear (actions)

#### Action Merging
- Groups actions by owner
- Merges similar actions from same owner
- Combines action text: "handle deployment" + "review dashboard" → "handle deployment and review dashboard"

### 5. Improved Pattern Matching ✅

#### Action Owner Detection
- Pattern 1: "Person will do X"
- Pattern 2: "assigned to Person"
- Pattern 3: "Person is responsible for"
- Pattern 4: Use speaker as owner
- Pattern 5: "I will" → use speaker
- Pattern 6: "we/team will" → look for assignment in context

#### Decision Participant Detection
- Extracts from "we", "team", "the group"
- Looks at nearby segments for other participants
- Uses NER to identify person names

#### Risk Categorization
- Timeline: delay, deadline, schedule
- Resource: budget, staff, capacity
- Data: quality, accuracy, missing
- Process: workflow, procedure
- Technical: system, integration, bug
- Other: catch-all

## Architecture

### Pipeline Flow

```
Raw Transcript
    ↓
Preprocessing (remove small talk, merge turns, remove fillers/repetitions)
    ↓
Intent Tagging (semantic clustering with embeddings)
    ↓
Specialized Extraction:
    ├─ DecisionExtractor (filtered by "decision" intent)
    ├─ ActionExtractor (filtered by "action" intent)
    └─ RiskExtractor (filtered by "risk" intent)
    ↓
Post-Processing (deduplication, merging, confidence filtering)
    ↓
Final Results
```

### Code Structure

```
backend/app/extraction/
├── extractor.py (main orchestrator)
└── specialized_extractors.py
    ├── IntentTagger
    ├── DecisionExtractor
    ├── ActionExtractor
    └── RiskExtractor
```

## Usage

The system automatically uses specialized extractors when `advanced` preprocessing is enabled:

```python
# In routes.py
processed_segments, metadata = cleaner.process(
    segments,
    remove_fillers=True,
    normalize_speakers=True,
    segment_topics=True,
    remove_small_talk=True,      # New!
    merge_short_turns=True       # New!
)

# In extractor.py - automatically uses specialized extractors
results = extractor.process(processed_segments)
```

## Results Structure

### Decisions
```json
{
  "decision": "We decided to push the rollout to next quarter",
  "rationale": "due to data quality issues",
  "participants": ["John", "Sarah"],
  "confidence": 0.93
}
```

### Action Items
```json
{
  "action": "handle deployment and review dashboard",
  "owner": "John",
  "due_date": "next Friday",
  "priority": "high",
  "confidence": 0.87
}
```

### Risks
```json
{
  "risk": "There's a risk of delay due to integration issues",
  "category": "Technical",
  "mentioned_by": "Sarah",
  "confidence": 0.85
}
```

## Performance Improvements

1. **Better Accuracy**: Intent tagging filters irrelevant sentences
2. **Fewer False Positives**: Specialized extractors focus on their domain
3. **Better Deduplication**: Semantic similarity catches near-duplicates
4. **Improved Owner Detection**: Multiple patterns + NER + context
5. **Cleaner Input**: Preprocessing removes noise before extraction

## Configuration

All models configured in `backend/app/config/settings.py`:
- `summarization_model`: For hierarchical summarization
- `ner_model`: `dslim/bert-base-NER` for entity extraction
- `embedding_model`: `sentence-transformers/all-MiniLM-L6-v2` for intent tagging

## Testing Recommendations

1. Test with transcripts containing:
   - Multiple speakers making decisions
   - Action items with unclear owners
   - Various risk categories
   - Small talk and repetitions

2. Verify:
   - Intent tagging correctly identifies decision/action/risk sentences
   - Deduplication merges similar items
   - Owner detection works for various patterns
   - Confidence scores are reasonable

## Future Enhancements

1. **Fine-tuning**: Train lightweight classifiers on labeled meeting samples
2. **Few-shot prompts**: Add examples to specialized prompts
3. **Cascading fallback**: Try larger models if confidence < threshold
4. **Evaluation metrics**: Add precision/recall tracking
5. **Custom intent examples**: Allow users to add domain-specific intent examples

## Backward Compatibility

- All changes are backward compatible
- Old extraction methods still exist (but not used)
- Falls back gracefully if embeddings unavailable
- Works with existing API endpoints

