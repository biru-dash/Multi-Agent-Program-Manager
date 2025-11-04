# Testing Guide for Meeting Intelligence Agent (MIA)

This guide will help you test the MIA system end-to-end.

## Prerequisites

1. **Backend Setup**:
   ```bash
   cd backend
   venv\Scripts\activate  # Windows
   # or: source venv/bin/activate  # Unix/MacOS
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create `backend/.env` file:
   ```env
   HUGGINGFACE_TOKEN=your_token_here
   MODEL_STRATEGY=hybrid
   UPLOAD_DIR=./uploads
   OUTPUT_DIR=./outputs
   MAX_FILE_SIZE_MB=50
   SUMMARIZATION_MODEL=knkarthick/bart-large-xsum-samsum
   NER_MODEL=dslim/bert-base-NER
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

3. **Frontend Setup**:
   ```bash
   npm install
   # Create .env file:
   echo "VITE_API_BASE_URL=http://localhost:8000" > .env
   ```

## Testing Steps

### 1. Start the Backend Server

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 2. Start the Frontend Server

In a new terminal:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 3. Test via Frontend UI

1. **Upload a Transcript**:
   - Open `http://localhost:5173`
   - Drag and drop one of the sample files from `backend/tests/`:
     - `sample_transcript.txt`
     - `sample_transcript.json`
     - `sample_transcript.srt`
   - Or click to browse and select a file

2. **Configure Settings**:
   - **Model Strategy**: 
     - `local`: Runs models locally (slower first time, needs models downloaded)
     - `hybrid`: Uses local models for extraction, HF API for summarization (recommended)
     - `remote`: Uses HuggingFace API for all tasks (requires valid token)
   - **Preprocessing**: 
     - `basic`: Minimal preprocessing
     - `advanced`: Full preprocessing with filler removal, speaker normalization, topic segmentation

3. **Process Transcript**:
   - Click "Process" button
   - Watch the workflow canvas for progress updates
   - Wait for processing to complete (may take 1-5 minutes depending on model strategy)

4. **Review Results**:
   - View the MIA Output tab to see:
     - Meeting Summary
     - Key Decisions (with confidence scores)
     - Action Items (with owners, due dates, priorities)
     - Identified Risks
     - Meeting Participants

5. **Export Results**:
   - Click "Export JSON" or "Export MARKDOWN" button
   - File will download automatically

### 4. Test via Python Script

Run the automated test script:

```bash
cd backend
venv\Scripts\activate
python test_api.py
```

This script will:
- Test health check endpoint
- Upload a sample transcript
- Process it with local models
- Poll for completion
- Retrieve and display results
- Test export functionality

### 5. Test via API Directly

#### Upload a file:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@backend/tests/sample_transcript.txt"
```

Response:
```json
{
  "upload_id": "uuid-here",
  "filename": "sample_transcript.txt",
  "size_mb": 0.05
}
```

#### Process the transcript:
```bash
curl -X POST "http://localhost:8000/api/process/{upload_id}?model_strategy=local&preprocessing=basic"
```

Response:
```json
{
  "job_id": "job-uuid-here",
  "status": "processing",
  "message": "Processing started..."
}
```

#### Check status:
```bash
curl "http://localhost:8000/api/status/{job_id}"
```

#### Get results:
```bash
curl "http://localhost:8000/api/results/{job_id}"
```

#### Export results:
```bash
curl "http://localhost:8000/api/export/{job_id}?format=json" -o report.json
curl "http://localhost:8000/api/export/{job_id}?format=md" -o report.md
```

## Test Cases

### Test Case 1: TXT Format
- File: `backend/tests/sample_transcript.txt`
- Expected: Should parse correctly, extract decisions, action items, and risks
- Verify: Decisions include "authentication module is our top priority"

### Test Case 2: JSON Format
- File: `backend/tests/sample_transcript.json`
- Expected: Should parse JSON structure correctly
- Verify: Participants list is extracted correctly

### Test Case 3: SRT Format
- File: `backend/tests/sample_transcript.srt`
- Expected: Should parse timestamps and speakers correctly
- Verify: Timestamps are preserved in output

### Test Case 4: Model Strategies
- Test with `local` strategy (slow but no API limits)
- Test with `hybrid` strategy (recommended, balances speed and quality)
- Test with `remote` strategy (requires valid HF token)

### Test Case 5: Preprocessing Levels
- Test with `basic` preprocessing (fast)
- Test with `advanced` preprocessing (removes fillers, normalizes speakers, segments topics)

## Troubleshooting

### Backend Issues

**Issue**: `ModuleNotFoundError: No module named 'app'`
- **Solution**: Make sure you're in the `backend` directory when running uvicorn

**Issue**: `ValueError: HUGGINGFACE_TOKEN is required`
- **Solution**: Create `backend/.env` file with your HuggingFace token

**Issue**: Models downloading slowly
- **Solution**: First run will download models (can be several GB). Subsequent runs use cached models.

**Issue**: `CUDA out of memory` or slow processing
- **Solution**: Models default to CPU. For GPU support, modify `device=-1` to `device=0` in adapter.py

### Frontend Issues

**Issue**: CORS errors
- **Solution**: Make sure backend CORS is configured for `http://localhost:5173`

**Issue**: Cannot connect to API
- **Solution**: Verify `VITE_API_BASE_URL` in `.env` matches your backend URL

**Issue**: Upload fails
- **Solution**: Check file size (max 50MB) and format (.txt, .json, .srt only)

## Expected Processing Times

- **Local Strategy (Basic)**: 30-60 seconds
- **Local Strategy (Advanced)**: 1-3 minutes
- **Hybrid Strategy**: 20-40 seconds (depends on HF API speed)
- **Remote Strategy**: 15-30 seconds (depends on HF API speed)

*Note: First run with local models will take longer as models are downloaded.*

## Success Criteria

✅ All test cases pass  
✅ Frontend can upload and process transcripts  
✅ Results display correctly with confidence scores  
✅ Export functionality works (JSON and Markdown)  
✅ Different file formats (TXT, JSON, SRT) work correctly  
✅ Model strategies work as expected  
✅ Preprocessing levels function correctly  

## Next Steps

After successful testing:
1. Try with your own meeting transcripts
2. Experiment with different model strategies
3. Review and refine confidence thresholds
4. Customize extraction prompts for your domain
5. Integrate with REA agent for full pipeline
