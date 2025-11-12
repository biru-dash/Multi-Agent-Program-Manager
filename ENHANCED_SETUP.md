# Enhanced MIA Setup Guide

This guide covers the setup for the enhanced Meeting Intelligence Agent (MIA) with Phase 1-3 capabilities including provenance tracking, punctuation restoration, and speaker diarization.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Git
- Optional: NVIDIA GPU for advanced models
- HuggingFace account (for some models)

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd Multi-Agent-Program-Manager
```

### 2. Backend Setup

#### Basic Installation
```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Enhanced Capabilities Setup

##### Speaker Diarization (PyAnnote)
```bash
# Install PyAnnote.Audio
pip install pyannote.audio

# Create HuggingFace token at https://huggingface.co/settings/tokens
# Accept terms for pyannote models at:
# https://huggingface.co/pyannote/speaker-diarization-3.1
# https://huggingface.co/pyannote/segmentation-3.0

# Set environment variable
export HUGGINGFACE_TOKEN="your_token_here"
```

##### Punctuation Restoration
```bash
# Already included in requirements.txt
# Models will be downloaded automatically on first use
```

##### Audio Processing (Optional)
```bash
# For audio transcript generation
pip install openai-whisper
```

##### Entity Recognition
```bash
# Install spaCy model
python -m spacy download en_core_web_sm
```

### 3. Environment Configuration

Create `.env` file in the backend directory:

```env
# Required
HUGGINGFACE_TOKEN=your_hf_token_here

# Model Strategy
MODEL_STRATEGY=local

# Optional: Model configurations (uses defaults if not specified)
SUMMARIZATION_MODEL=llama3.2
DIARIZATION_MODEL=pyannote/speaker-diarization-3.1
PUNCTUATION_MODEL=oliverguhr/fullstop-punctuation-multilang-large
EMBEDDING_MODEL=all-mpnet-base-v2

# Advanced settings
MIA_SKIP_EMBEDDING_MODEL=false
ENABLE_DIARIZATION=true
ENABLE_PUNCTUATION_RESTORATION=true
ENABLE_COREFERENCE_RESOLUTION=true
```

### 4. Frontend Setup

```bash
cd ../frontend  # or just cd .. if in backend
npm install
```

## Model Configuration

The enhanced MIA supports step-specific model configuration. You can configure different models for each pipeline step.

### Available Model Providers

1. **Summarization**: `ollama`, `openai`, `huggingface`
2. **Diarization**: `pyannote`, `simple` (rule-based)
3. **Punctuation**: `local` (transformer-based), `rule_based`
4. **Embedding**: `sentence_transformers`
5. **Entity Recognition**: `spacy`, `huggingface`

### Configuration via API

```bash
# Check current model status
curl http://localhost:8000/api/models/status

# Update model configuration
curl -X POST http://localhost:8000/api/models/config \
  -H "Content-Type: application/json" \
  -d '{
    "step": "diarization",
    "provider": "pyannote",
    "model": "pyannote/speaker-diarization-3.1",
    "fallback": "simple"
  }'

# Test model functionality
curl -X POST http://localhost:8000/api/models/test/diarization
```

### Configuration via Settings File

Update `backend/app/config/settings.py`:

```python
models: Dict[str, Dict[str, str]] = {
    "summarization": {
        "provider": "ollama",
        "model": "llama3.2",
        "fallback": "llama3"
    },
    "diarization": {
        "provider": "pyannote",
        "model": "pyannote/speaker-diarization-3.1", 
        "fallback": "simple"
    },
    # ... other models
}
```

## Running the Enhanced System

### 1. Start Ollama (if using Ollama models)
```bash
# Install Ollama first: https://ollama.ai
ollama serve
ollama pull llama3.2  # or your preferred model
```

### 2. Start Backend
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend
```bash
cd frontend  # or root directory
npm run dev
```

### 4. Access Application
- Frontend: http://localhost:8080 (or shown port)
- API Docs: http://localhost:8000/docs
- Model Management: http://localhost:8000/api/models/status

## Enhanced Features Usage

### Provenance Tracking

All extractions now include provenance information showing source segments:

```json
{
  "decision": "Push launch date to October 29th",
  "confidence": 0.9,
  "provenance": {
    "source_segment_ids": [42, 43],
    "source_text": ["We need to push the launch...", "October 29th works better..."],
    "similarity_scores": [0.85, 0.92],
    "extraction_method": "llm"
  },
  "validation": {
    "is_valid": true,
    "source_support": 0.85,
    "potential_hallucination": false
  }
}
```

### Audio Processing

Process audio files directly:

```python
from app.preprocessing.enhanced_pipeline import enhanced_pipeline

# Process audio file
segments, metadata = enhanced_pipeline.process_audio_file(
    "meeting_audio.wav",
    calendar_metadata={
        "participants": ["Alice Smith", "Bob Johnson", "Carol Davis"]
    }
)
```

### Speaker Diarization

With audio files and calendar metadata:

```python
# Upload audio file via API with calendar data
{
  "audio_path": "/path/to/meeting.wav",
  "calendar_metadata": {
    "participants": ["Alice Smith", "Bob Johnson"],
    "meeting_title": "Q4 Planning",
    "duration": 45
  }
}
```

### Punctuation Restoration

Automatically applied to all transcripts:

```
Input: "so um david can you give us an update on the project yeah sure"
Output: "So, David, can you give us an update on the project? Yeah, sure."
```

## Troubleshooting

### Common Issues

1. **PyAnnote Token Issues**
   ```bash
   # Verify token
   python -c "from huggingface_hub import HfApi; print(HfApi().whoami(token='your_token'))"
   
   # Re-accept model terms
   # Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
   ```

2. **Model Download Failures**
   ```bash
   # Clear cache and retry
   rm -rf ~/.cache/huggingface/
   rm -rf ~/.cache/torch/
   pip install --upgrade transformers
   ```

3. **Memory Issues**
   ```bash
   # Reduce model sizes in settings
   EMBEDDING_MODEL=all-MiniLM-L6-v2  # Smaller model
   PUNCTUATION_MODEL=rule_based      # Use rules instead
   ```

4. **Audio Processing Issues**
   ```bash
   # Install additional audio dependencies
   pip install librosa soundfile
   ```

### Performance Optimization

1. **GPU Acceleration**
   ```bash
   # Install CUDA-enabled PyTorch
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Model Caching**
   ```python
   # Models are cached after first load
   # Location: ~/.cache/huggingface/
   # To clear: rm -rf ~/.cache/huggingface/
   ```

3. **Batch Processing**
   ```python
   # Process multiple files efficiently
   from app.preprocessing.enhanced_pipeline import enhanced_pipeline
   
   for file_path in transcript_files:
       segments, metadata = enhanced_pipeline.process_transcript(file_path)
   ```

## API Endpoints

### Enhanced Endpoints

- `GET /api/models/status` - Model health check
- `GET /api/models/config` - Current configuration  
- `POST /api/models/config` - Update configuration
- `GET /api/models/capabilities` - Pipeline capabilities
- `POST /api/models/test/{step}` - Test specific model

### Processing Options

```bash
# Process with enhanced options
curl -X POST "http://localhost:8000/api/process/{upload_id}?model_strategy=hybrid&preprocessing=advanced" \
  -d '{
    "enable_diarization": true,
    "enable_punctuation_restoration": true,
    "enable_coreference_resolution": true,
    "remove_fillers": true,
    "calendar_metadata": {
      "participants": ["Alice", "Bob", "Carol"]
    }
  }'
```

## Development

### Adding New Models

1. **Create Model Adapter**
   ```python
   # In app/models/your_model.py
   class YourModelAdapter:
       def __init__(self, model_name: str):
           # Initialize your model
           pass
       
       def process(self, text: str):
           # Your processing logic
           pass
   ```

2. **Register in Model Manager**
   ```python
   # In app/models/model_manager.py
   self._providers['your_provider'] = YourModelAdapter
   ```

3. **Update Configuration**
   ```python
   # In app/config/settings.py
   "your_step": {
       "provider": "your_provider",
       "model": "your_model",
       "fallback": "simple"
   }
   ```

### Testing

```bash
# Run enhanced tests
cd backend
python -m pytest tests/ -v

# Test specific components
python test_complete_extraction.py
python debug_actions.py
```

## Security Considerations

1. **HuggingFace Token**: Keep your HF token secure and don't commit it to version control
2. **Model Downloads**: Models are downloaded to `~/.cache/` - ensure adequate disk space
3. **API Access**: Configure CORS appropriately for production
4. **Audio Files**: Be cautious with audio file uploads in production environments

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API docs at `/docs` endpoint  
3. Check model status at `/api/models/status`
4. Review logs for detailed error information