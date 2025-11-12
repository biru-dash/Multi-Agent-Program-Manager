# MIA Next Steps - Implementation Roadmap

## Current Implementation Status

### Implemented Features
- Basic speaker extraction from pre-formatted transcripts
- Speaker normalization to canonical forms
- Filler word and repetition removal
- Semantic segmentation using embeddings
- Rule-based and LLM-based extraction
- Hierarchical summarization
- Basic UI for displaying results

### Missing Components
- Advanced diarization with speaker identification
- Punctuation restoration and coreference resolution
- Fine-tuned action/decision classifiers
- Locate-then-summarize retrieval system
- Provenance tracking and UI
- Human-in-the-loop validation

## End-to-End Pipeline Mapping

### Step 1: Audio/Transcript Ingestion
**File**: `backend/app/preprocessing/ingestion.py`
**Purpose**: Accept multiple input formats (audio files, raw ASR output, formatted transcripts)
**Why Important**: Flexibility in input sources enables broader adoption
**How it Works**: 
- Detect input format (audio, JSON, TXT, SRT)
- Convert audio to text if needed using ASR
- Standardize format for downstream processing

**Best Models**:
- ASR: Whisper (OpenAI), Wav2Vec2, or cloud services (Google Speech-to-Text)
- Format detection: Rule-based file extension and content analysis

**Example Input**:
```
Audio file: meeting_2024_01_15.wav
or
Raw ASR: "so um david can you give us an update on the project yeah sure so we've made good progress"
```

**Example Output**:
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "so um david can you give us an update on the project",
      "speaker": null
    },
    {
      "start": 5.2,
      "end": 10.1,
      "text": "yeah sure so we've made good progress",
      "speaker": null
    }
  ]
}
```

### Step 2: Speaker Diarization
**File**: `backend/app/preprocessing/diarizer.py`
**Purpose**: Identify who spoke when in the meeting
**Why Important**: Critical for action item ownership and decision attribution
**How it Works**:
- Process audio to identify speaker segments
- Cluster similar voice embeddings
- Assign consistent speaker IDs
- Link to calendar metadata for name resolution

**Best Models**:
- pyannote.audio 3.0 (state-of-the-art)
- NVIDIA NeMo speaker diarization
- Google Cloud Speaker Diarization API

**Example Input**:
```json
{
  "audio_path": "meeting_audio.wav",
  "calendar_metadata": {
    "participants": ["David Chen", "Sarah Miller", "Marcus Johnson"]
  }
}
```

**Example Output**:
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "so um david can you give us an update on the project",
      "speaker": "Sarah Miller",
      "speaker_confidence": 0.92
    },
    {
      "start": 5.2,
      "end": 10.1,
      "text": "yeah sure so we've made good progress",
      "speaker": "David Chen",
      "speaker_confidence": 0.88
    }
  ]
}
```

### Step 3: Text Normalization
**File**: `backend/app/preprocessing/normalizer.py`
**Purpose**: Clean and enhance transcript quality
**Why Important**: Improves downstream NLP accuracy and readability
**How it Works**:
- Restore punctuation and capitalization
- Resolve pronouns to actual names
- Fix common ASR errors
- Remove disfluencies while preserving meaning

**Best Models**:
- Punctuation: Silero Punctuation, FullStop, or fine-tuned BERT
- Coreference: NeuralCoref, SpanBERT, or LLM-based
- Error correction: Custom n-gram models or LLM-based

**Example Input**:
```
"yeah sure so we've made good progress he said we should launch by october 15th but i think we need more time"
```

**Example Output**:
```
"Yeah, sure. So we've made good progress. David said we should launch by October 15th, but I think we need more time."
```

### Step 4: Semantic Chunking & Segmentation
**File**: `backend/app/preprocessing/chunker.py`
**Purpose**: Group utterances into coherent topics and semantic units
**Why Important**: Enables focused extraction and prevents context mixing
**How it Works**:
- Compute embeddings for utterance windows
- Detect topic boundaries using similarity thresholds
- Create overlapping chunks for context preservation
- Maintain speaker and temporal information

**Best Models**:
- Embeddings: all-MiniLM-L6-v2, all-mpnet-base-v2
- Segmentation: TextTiling, C99, or transformer-based

**Example Input**:
```json
{
  "segments": [
    {"text": "Let's discuss the timeline.", "speaker": "Sarah"},
    {"text": "We have three deliverables.", "speaker": "Sarah"},
    {"text": "First is the API integration.", "speaker": "Sarah"},
    {"text": "Moving on to risks.", "speaker": "Marcus"},
    {"text": "I'm concerned about the security audit.", "speaker": "Marcus"}
  ]
}
```

**Example Output**:
```json
{
  "topics": [
    {
      "id": "topic_1",
      "theme": "timeline_and_deliverables",
      "segments": [0, 1, 2],
      "embedding": [0.23, -0.45, ...]
    },
    {
      "id": "topic_2", 
      "theme": "risks_and_concerns",
      "segments": [3, 4],
      "embedding": [0.67, 0.12, ...]
    }
  ]
}
```

### Step 5: Action/Decision Detection
**File**: `backend/app/extraction/detectors.py`
**Purpose**: Identify and extract actionable items and decisions
**Why Important**: Core value of meeting intelligence - capturing commitments
**How it Works**:
- Apply fine-tuned classifiers to identify action/decision spans
- Extract entities (WHO, WHAT, WHEN) using NER and patterns
- Calculate confidence scores based on linguistic features
- Cross-reference with speaker information

**Best Models**:
- Span detection: Fine-tuned BERT/RoBERTa on AMI corpus
- Temporal extraction: SUTime, HeidelTime, or Duckling
- Entity recognition: spaCy NER or custom BERT-NER

**Example Input**:
```
"Sarah, can you send the requirements doc to the client by Friday? I'll set up the review meeting for next Monday."
```

**Example Output**:
```json
{
  "actions": [
    {
      "type": "action_item",
      "text": "send the requirements doc to the client",
      "owner": "Sarah",
      "due_date": "Friday",
      "due_date_parsed": "2024-01-19",
      "confidence": 0.94,
      "source_segment_id": 42
    },
    {
      "type": "action_item",
      "text": "set up the review meeting",
      "owner": "Speaker_1",
      "due_date": "next Monday",
      "due_date_parsed": "2024-01-22",
      "confidence": 0.91,
      "source_segment_id": 42
    }
  ]
}
```

### Step 6: Risk & Concern Extraction
**File**: `backend/app/extraction/risk_extractor.py`
**Purpose**: Identify potential problems and blockers
**Why Important**: Proactive risk management and issue tracking
**How it Works**:
- Detect risk indicators using patterns and classifiers
- Categorize by type (timeline, technical, resource, etc.)
- Extract impact levels and mitigation strategies
- Link to speakers who raised concerns

**Best Models**:
- Risk detection: Fine-tuned classifiers or few-shot LLM prompting
- Categorization: Multi-label classification with BERT
- Sentiment analysis: For gauging concern severity

**Example Input**:
```
"I'm worried about the API performance. We're seeing 10-second response times with large datasets, which could block the enterprise rollout."
```

**Example Output**:
```json
{
  "risks": [
    {
      "risk": "API performance issues with large datasets",
      "details": "10-second response times",
      "category": "Technical",
      "impact": "High",
      "affected_item": "enterprise rollout",
      "raised_by": "David Chen",
      "confidence": 0.88,
      "source_segment_id": 67
    }
  ]
}
```

### Step 7: Retrieval-Augmented Summarization
**File**: `backend/app/extraction/summarizer.py`
**Purpose**: Generate focused, accurate meeting summaries
**Why Important**: Provides quick overview while maintaining factual accuracy
**How it Works**:
- Index all segments with embeddings
- For each summary aspect (decisions, actions, general), retrieve relevant segments
- Feed retrieved context to summarization model
- Ensure factual grounding and prevent hallucination

**Best Models**:
- Retrieval: FAISS with sentence-transformers embeddings
- Summarization: BART, T5, Longformer, or GPT-based
- Long context: LED (Longformer Encoder-Decoder)

**Example Input**:
```json
{
  "query": "decisions about launch timeline",
  "segment_embeddings": [[0.23, -0.45, ...], ...],
  "segments": [...]
}
```

**Example Output**:
```json
{
  "summary": "The team decided to push the product launch from October 15th to October 29th to allow for additional security testing and performance optimization. This 2-week delay will provide buffer time for resolving the identified API performance issues.",
  "source_segments": [23, 45, 67],
  "confidence": 0.92
}
```

### Step 8: Synthesis & Quality Validation
**File**: `backend/app/extraction/synthesizer.py`
**Purpose**: Combine all extractions into coherent output
**Why Important**: Ensures consistency and completeness
**How it Works**:
- Merge related items across extraction types
- Resolve conflicts and duplicates
- Validate against source material
- Generate executive summary with all components

**Best Models**:
- Deduplication: Semantic similarity with transformers
- Validation: Entailment models (NLI) for fact-checking
- Synthesis: Large language models with structured prompts

**Example Input**:
```json
{
  "decisions": [...],
  "actions": [...],
  "risks": [...],
  "summary_chunks": [...],
  "metadata": {...}
}
```

**Example Output**:
```json
{
  "executive_summary": "The Q4 planning meeting was a 45-minute session...",
  "decisions": [...],
  "action_items": [...],
  "risks": [...],
  "quality_score": 0.89,
  "provenance_map": {...}
}
```

### Step 9: Provenance & UI Presentation
**File**: `frontend/src/components/ProvenanceView.tsx`
**Purpose**: Show traceable links between extractions and source
**Why Important**: Builds trust and enables validation
**How it Works**:
- Map each extracted item to source segments
- Highlight relevant portions in original transcript
- Enable user confirmation/correction
- Collect feedback for model improvement

**Best Models**:
- UI Framework: React with interactive highlighting
- Alignment: Token-level alignment between summary and source
- Feedback: Active learning pipeline

**Example UI Flow**:
```
Action Item: "Send requirements doc by Friday"
[Show Source] ’ Highlights: "Sarah, can you send the requirements..."
[Confirm ] [Edit] [Wrong Owner] [Wrong Date]
```

### Step 10: Human-in-the-Loop Refinement
**File**: `backend/app/feedback/collector.py`
**Purpose**: Continuous improvement through user feedback
**Why Important**: Adapts to organization-specific patterns
**How it Works**:
- Collect corrections and confirmations
- Store feedback with context
- Retrain models periodically
- A/B test improvements

**Best Models**:
- Active Learning: Uncertainty sampling for model updates
- Fine-tuning: LoRA or full fine-tuning based on feedback volume
- Evaluation: Human evaluation metrics

**Example Feedback Loop**:
```json
{
  "item_id": "action_123",
  "original": {
    "owner": "Sarah",
    "action": "send requirements"
  },
  "correction": {
    "owner": "Sam Wilson",
    "action": "send requirements and test plan"
  },
  "confidence_delta": -0.15
}
```

## Implementation Priority

1. **Phase 1** (Immediate): Provenance tracking, basic validation
2. **Phase 2** (Short-term): Punctuation restoration, enhanced chunking
3. **Phase 3** (Medium-term): Diarization, fine-tuned classifiers
4. **Phase 4** (Long-term): Full retrieve-then-summarize, active learning

This pipeline ensures high-quality, trustworthy meeting intelligence with clear paths for continuous improvement.