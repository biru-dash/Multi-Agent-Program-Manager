# MIA Agent Improvements - Modular Multi-stage Architecture

## Overview
This document outlines the comprehensive improvements made to the Meeting Intelligence Assistant (MIA) agent to address accuracy issues and implement a robust, modular multi-stage architecture.

## Improvements Implemented

### Stage 1: Enhanced Transcript Preprocessing ✅

**Location:** `backend/app/preprocessing/cleaner.py`

#### Semantic Chunking
- Added `semantic_chunk()` method that uses sentence-transformers embeddings
- Intelligently chunks text at semantic boundaries (500-700 tokens per chunk)
- Uses cosine similarity to detect topic shifts
- Falls back to simple word-based chunking if embeddings unavailable

**Key Features:**
- Chunk size: 650 tokens (max), 300 tokens (min)
- Semantic similarity threshold: 0.7
- Preserves sentence boundaries
- Handles long transcripts gracefully

#### Enhanced Cleaning
- Existing filler word removal (enhanced)
- Speaker normalization
- Topic segmentation using embeddings

### Stage 2: Hierarchical Summarization ✅

**Location:** `backend/app/extraction/extractor.py`

#### Improved Chunking Strategy
- Uses semantic chunking (500-700 tokens) instead of simple word-based
- Better handling of model context windows
- Recursive chunking for very long inputs

#### Hierarchical Approach
1. **Chunk-level summarization**: Each ~650-token chunk is summarized (120 tokens output)
2. **Meta-summarization**: All chunk summaries are combined and summarized again (200 tokens output)
3. **Fallback logic**: If a chunk fails, it's recursively split and processed

#### Robust Error Handling
- Handles `RuntimeError` for input too long
- Recursive chunking when individual chunks exceed limits
- Continues processing even if some chunks fail
- Graceful degradation with meaningful error messages

### Stage 3: Enhanced Information Extraction ✅

**Location:** `backend/app/extraction/extractor.py`

#### NER Integration
- Uses `dslim/bert-base-NER` for entity extraction
- Extracts person names (PER) and organizations (ORG)
- Better speaker identification from extracted entities
- Improved owner detection for action items

#### Pattern Matching Improvements
- Enhanced regex patterns for action item extraction:
  - "Person will do X"
  - "assigned to Person"
  - "we/team/I will do X"
  - "Person should/needs to do X"
- Better due date detection with multiple patterns
- Priority detection from keywords

#### Embedding-Based Extraction
- Uses sentence embeddings to identify action-like sentences
- Clusters semantically similar segments
- Better context understanding

### Stage 4: Semantic Confidence Scoring ✅

**Location:** `backend/app/extraction/extractor.py`

#### Implementation
- Uses cosine similarity between extracted items and meeting summary
- Confidence mapping:
  - High (0.9): Similarity > 0.7
  - Medium (0.7): Similarity > 0.5
  - Medium-Low (0.5): Similarity > 0.3
  - Low (0.4): Similarity ≤ 0.3

#### Fallback
- If embeddings unavailable, falls back to keyword-based confidence
- Uses explicit language detection ("will", "decided", "must") for high confidence

### Stage 5: Quality Detection & Fallback Chain ✅

**Location:** `backend/app/extraction/extractor.py` and `backend/app/api/routes.py`

#### Quality Metrics
Calculates:
- Summary length
- Number of decisions, actions, risks extracted
- Average confidence score
- Redundancy ratio (repeated phrases)

#### Quality Thresholds
Flags low quality if:
- Redundancy ratio > 0.3
- Total extracted items (decisions + actions) < 5
- Average confidence < 0.5

#### Automatic Fallback
- When using `local` strategy and quality is low:
  1. Automatically attempts fallback to remote API (HuggingFace)
  2. Re-extracts summary with remote model
  3. Re-processes structured data
  4. Recalculates quality metrics
  5. Updates results if quality improves

#### Fallback Chain
1. Local model (primary for local strategy)
2. Remote API (if quality low or local fails)
3. Graceful degradation with error messages

## Model Adapter Enhancements ✅

**Location:** `backend/app/models/adapter.py`

### Added Methods
- `get_embedding_model()` for `LocalTransformerAdapter`
- Already exists for `HybridAdapter`

### Embedding Model Access
- All adapters can now provide embedding models for confidence scoring
- Uses `sentence-transformers/all-MiniLM-L6-v2` by default
- Cached locally for performance

## Configuration

### Models Used
- **Summarization**: `philschmid/bart-large-cnn-samsum` (fine-tuned for conversations)
- **NER**: `dslim/bert-base-NER` (person, org, location, misc)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (fast, accurate)

### Settings
All models configured in `backend/app/config/settings.py`:
- `summarization_model`: BART model for summarization
- `ner_model`: BERT model for entity extraction
- `embedding_model`: Sentence transformer for embeddings

## Usage

### Automatic Quality Detection
The system automatically:
1. Processes transcript with chosen strategy
2. Calculates quality metrics
3. Triggers fallback if quality is low (local strategy only)
4. Reports quality metrics in results

### Results Structure
Results now include:
```json
{
  "summary": "...",
  "decisions": [...],
  "action_items": [...],
  "risks": [...],
  "quality_metrics": {
    "summary_length": 250,
    "decisions_count": 5,
    "actions_count": 8,
    "risks_count": 3,
    "avg_confidence": 0.75,
    "redundancy_ratio": 0.15
  },
  "quality_warning": false,
  "used_fallback": false,
  "metadata": {...}
}
```

## Performance Improvements

1. **Semantic Chunking**: Better chunk boundaries = better summaries
2. **Hierarchical Summarization**: Handles long transcripts without information loss
3. **NER Integration**: More accurate entity extraction
4. **Confidence Scoring**: Better quality assessment
5. **Quality Detection**: Automatic fallback improves results

## Dependencies

All required dependencies are already in `requirements.txt`:
- `sentence-transformers>=2.2.2` (for embeddings)
- `scikit-learn>=1.3.2` (for cosine similarity)
- `transformers>=4.35.0` (for NER and summarization)
- `numpy>=1.24.3` (for numerical operations)

## Testing Recommendations

1. Test with long transcripts (>5000 words)
2. Test with transcripts containing multiple speakers
3. Test quality detection with intentionally poor inputs
4. Verify fallback chain works correctly
5. Check confidence scores are reasonable

## Future Enhancements

1. Fine-tune summarization model on meeting dataset
2. Add topic segmentation before summarization
3. Integrate speaker diarization (WhisperX or pyannote.audio)
4. Add evaluation metrics (ROUGE, BLEU, repetition score)
5. Cache remote API outputs to reduce costs

## Backward Compatibility

All changes are backward compatible:
- Existing API endpoints unchanged
- Default behavior maintained
- Quality detection is additive (doesn't break existing flows)
- Fallback is optional and only triggers when needed


