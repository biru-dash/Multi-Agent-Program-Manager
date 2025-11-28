# Local Models Configuration

This document describes the recommended local models for optimal performance and accuracy.

## Model Configuration

### Summarization: `philschmid/bart-large-cnn-samsum`
- **Size**: ~1.6 GB
- **Framework**: Transformers (PyTorch)
- **Why it's good**: 
  - Tuned specifically for conversational text (SAMSum dataset)
  - Abstractive summarization (not just extraction)
  - 1024-token limit manageable for chunked meetings
  - Better for meeting transcripts than general news summarization

### Named Entity Recognition: `dslim/bert-base-NER`
- **Size**: ~400 MB
- **Framework**: Transformers (PyTorch)
- **Why it's good**:
  - Compact and efficient
  - Highly accurate
  - Trained on CoNLL-03 dataset
  - Standard labels: PER (Person), ORG (Organization), LOC (Location), MISC (Miscellaneous)

### Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- **Size**: ~100 MB
- **Framework**: SentenceTransformers
- **Why it's good**:
  - Fast CPU inference
  - Great trade-off between speed and quality
  - Optimized for semantic search
  - 384-dimensional embeddings

### Zero-shot Classification: `facebook/bart-large-mnli`
- **Size**: ~1.6 GB
- **Framework**: Transformers (PyTorch)
- **Why it's good**:
  - Reliable general-purpose zero-shot classification
  - Works well for categorizing decisions, actions, risks
  - Multi-Genre Natural Language Inference (MNLI) trained

## Total Storage Requirements

- **Total**: ~3.7 GB
- Models are cached in `backend/models_cache/` after first download
- Subsequent runs use cached models (no re-download)

## Performance Notes

### CPU Inference
- All models are optimized for CPU inference (device=-1)
- First run may be slower as models are downloaded
- Subsequent runs are faster with cached models

### Memory Requirements
- Minimum: 4GB RAM
- Recommended: 8GB+ RAM for smooth operation
- Models are loaded lazily (only when needed)

## Configuration Files

### Default Configuration (`backend/app/config/settings.py`)
```python
summarization_model: str = "philschmid/bart-large-cnn-samsum"
ner_model: str = "dslim/bert-base-NER"
embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
```

### Environment Variables (`backend/.env`)
```env
SUMMARIZATION_MODEL=philschmid/bart-large-cnn-samsum
NER_MODEL=dslim/bert-base-NER
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Model Strategy Options

### Local Strategy
- Uses all models locally
- No API calls required
- Works offline after initial download
- Slower but more reliable

### Hybrid Strategy (Recommended)
- Uses InferenceClient API for summarization (when available)
- Falls back to local models if API fails
- Best of both worlds: speed + reliability

### Remote Strategy
- Uses HuggingFace Inference API for all tasks
- Fastest but requires internet
- May have rate limits or availability issues

## Updating Models

To change models, update either:
1. `backend/app/config/settings.py` (default values)
2. `backend/.env` (environment-specific overrides)

Then restart the backend server.

## Model Caching

Models are automatically cached in:
- `backend/models_cache/` (Transformers models)
- `~/.cache/huggingface/` (default HuggingFace cache)

To clear cache and re-download:
```bash
rm -rf backend/models_cache/
```

## Troubleshooting

### Model Download Issues
- Check internet connection
- Verify sufficient disk space (~4GB)
- Check HuggingFace token if using private models

### Out of Memory Errors
- Use smaller models
- Process shorter transcripts
- Consider using API strategy instead

### Slow Performance
- First run downloads models (expected)
- Use GPU if available (set `device=0` in adapter.py)
- Consider using hybrid strategy for faster API calls

