# Testing Local Models

## Configuration

The system is now configured to use **local models only** for testing.

### Current Settings

- **Model Strategy**: `local` (all models run locally)
- **Summarization**: `philschmid/bart-large-cnn-samsum` (~1.6 GB)
- **NER**: `dslim/bert-base-NER` (~400 MB)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (~100 MB)
- **Classification**: `facebook/bart-large-mnli` (~1.6 GB)

**Total Size**: ~3.7 GB (downloaded once, then cached)

## How to Test

### 1. Start Backend Server

```bash
./start-backend.sh
```

### 2. Start Frontend Server (in another terminal)

```bash
./start-frontend.sh
```

### 3. Test with a Transcript

1. Open the frontend: http://localhost:8080 (or the port shown)
2. Go to the "From Folder" tab
3. Select a transcript file from `meeting_transcripts/` folder
4. Click "Process Transcript"
5. Watch the backend logs for model download progress

## What to Expect

### First Run
- Models will be downloaded (one-time, ~3.7 GB total)
- First download may take 5-15 minutes depending on internet speed
- Progress shown in backend logs
- Models cached in `backend/models_cache/` for future use

### Subsequent Runs
- Models load from cache (much faster)
- No re-download needed
- Processing should be faster

## Backend Logs to Watch

You'll see messages like:
```
Device set to use cpu
Loading model: philschmid/bart-large-cnn-samsum
Downloading config.json...
Downloading model.safetensors...
```

## Model Download Locations

- **Transformers models**: `backend/models_cache/`
- **SentenceTransformers**: `~/.cache/huggingface/`

## Testing Checklist

- [ ] Backend server started successfully
- [ ] Frontend server started successfully
- [ ] Models downloading (first run) or loading from cache
- [ ] Transcript file selected from folder
- [ ] Processing started
- [ ] Summary generated successfully
- [ ] Decisions extracted
- [ ] Action items extracted
- [ ] Risks identified
- [ ] Results displayed in frontend

## Troubleshooting

### Model Download Fails
- Check internet connection
- Verify sufficient disk space (~4GB)
- Check HuggingFace token (if using private models)

### Out of Memory
- Models require ~4GB RAM minimum
- Close other applications
- Try processing shorter transcripts

### Slow Processing
- First run downloads models (expected)
- CPU inference is slower than GPU
- Consider using shorter transcripts for testing

### Model Not Found Errors
- Verify model names in `.env` file
- Check HuggingFace for model availability
- Ensure model names match exactly (case-sensitive)

## Switching Back to Hybrid

To switch back to hybrid mode (API + local fallback):

1. Update `.env`:
   ```env
   MODEL_STRATEGY=hybrid
   ```

2. Or change in `backend/app/config/settings.py`:
   ```python
   model_strategy: Literal["local", "remote", "hybrid"] = "hybrid"
   ```

3. Restart backend server

## Performance Notes

### Local Models (Current Setup)
- ✅ Works offline after download
- ✅ No API rate limits
- ✅ More reliable
- ❌ Slower than API (CPU inference)
- ❌ First download takes time

### Hybrid Mode (Alternative)
- ✅ Fast API calls when available
- ✅ Automatic fallback to local
- ✅ Best of both worlds
- ❌ Requires internet for API
- ❌ May have API availability issues

## Next Steps After Testing

1. Verify all models work correctly
2. Test with different transcript lengths
3. Check extraction quality
4. Consider switching to hybrid mode for production (faster)

