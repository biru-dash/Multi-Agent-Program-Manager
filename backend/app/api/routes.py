"""FastAPI routes for Meeting Intelligence Agent."""
import asyncio
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import aiofiles

from app.config.settings import settings
from app.preprocessing.parser import TranscriptParser
from app.preprocessing.cleaner import get_cleaner
from app.models.adapter import get_model_adapter
from app.extraction.extractor import MeetingExtractor
from app.utils.storage import StorageManager

router = APIRouter(prefix="/api", tags=["mia"])

# In-memory job status tracking (for MVP)
# In production, use Redis or database
job_status = {}
job_results = {}

storage = StorageManager(
    output_dir=settings.output_dir,
    upload_dir=settings.upload_dir
)


class ProcessRequest(BaseModel):
    """Request model for processing."""
    model_strategy: Optional[str] = "hybrid"
    preprocessing: Optional[str] = "advanced"


@router.post("/upload")
async def upload_transcript(file: UploadFile = File(...)):
    """Upload a transcript file (txt, json, srt)."""
    # Validate file type
    allowed_extensions = {'.txt', '.json', '.srt'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    
    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )
    
    # Save file
    upload_id = storage.save_upload(contents, file.filename)
    
    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size_mb": round(file_size_mb, 2)
    }


@router.post("/process/{upload_id}")
async def process_transcript(
    upload_id: str,
    model_strategy: Optional[str] = Query("hybrid", enum=["local", "remote", "hybrid"]),
    preprocessing: Optional[str] = Query("advanced", enum=["basic", "advanced"])
):
    """Process uploaded transcript and extract meeting intelligence."""
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Starting processing..."
    }
    
    # Run processing in background
    asyncio.create_task(process_job(job_id, upload_id, model_strategy, preprocessing))
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Processing started. Poll /api/status/{job_id} for updates."
    }


async def process_job(job_id: str, upload_id: str, model_strategy: str, preprocessing: str):
    """Background job processor."""
    try:
        job_status[job_id]["progress"] = 10
        job_status[job_id]["message"] = "Loading transcript..."
        
        # Get file path
        file_path = storage.get_upload_path(upload_id)
        
        # Parse transcript
        segments = TranscriptParser.parse(str(file_path))
        
        job_status[job_id]["progress"] = 30
        job_status[job_id]["message"] = "Preprocessing transcript..."
        
        # Preprocess
        advanced = preprocessing == "advanced"
        cleaner = get_cleaner()
        processed_segments, preprocess_metadata = cleaner.process(
            segments,
            remove_fillers=advanced,
            normalize_speakers=advanced,
            segment_topics=advanced
        )
        
        job_status[job_id]["progress"] = 50
        job_status[job_id]["message"] = "Initializing models..."
        
        # Get model adapter with specified strategy
        # Temporarily modify settings for this request
        original_strategy = settings.model_strategy
        from app.config.settings import Settings
        temp_settings = Settings()
        temp_settings.model_strategy = model_strategy
        
        # Import and use get_model_adapter with override
        from app.models.adapter import LocalTransformerAdapter, HuggingFaceInferenceAdapter, HybridAdapter
        
        if model_strategy == "local":
            model_adapter = LocalTransformerAdapter()
        elif model_strategy == "remote":
            model_adapter = HuggingFaceInferenceAdapter(settings.huggingface_token)
        else:  # hybrid
            model_adapter = HybridAdapter(settings.huggingface_token)
        
        job_status[job_id]["progress"] = 60
        job_status[job_id]["message"] = "Extracting meeting intelligence..."
        
        # Extract information
        extractor = MeetingExtractor(model_adapter, cleaner)
        results = extractor.process(processed_segments)
        
        job_status[job_id]["progress"] = 80
        job_status[job_id]["message"] = "Saving results..."
        
        # Add preprocessing metadata
        results["preprocessing_metadata"] = preprocess_metadata
        
        # Save results
        try:
            storage.save_results(job_id, results)
            job_results[job_id] = results
            job_status[job_id]["progress"] = 100
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["message"] = "Processing complete!"
        except Exception as save_error:
            # Even if save fails, try to keep results in memory
            job_results[job_id] = results
            job_status[job_id]["progress"] = 95
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["message"] = f"Processing complete (save warning: {str(save_error)})"
            print(f"Warning: Could not save results to disk for job {job_id}: {save_error}")
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error processing job {job_id}: {error_trace}")
        
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["message"] = f"Error: {str(e)}"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["progress"] = 0


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get processing results."""
    print(f"[DEBUG] Getting results for job_id: {job_id}")
    print(f"[DEBUG] Available jobs in memory: {list(job_results.keys())}")
    
    if job_id not in job_results:
        # Try loading from storage
        print(f"[DEBUG] Job {job_id} not in memory, trying to load from storage...")
        try:
            results = storage.get_results(job_id)
            job_results[job_id] = results
            print(f"[DEBUG] Successfully loaded results from storage for job {job_id}")
        except FileNotFoundError as e:
            print(f"[DEBUG] Results not found in storage for job {job_id}: {e}")
            print(f"[DEBUG] Job status: {job_status.get(job_id, 'NOT FOUND')}")
            raise HTTPException(status_code=404, detail=f"Results not found for job {job_id}")
        except Exception as e:
            print(f"[DEBUG] Error loading results: {e}")
            raise HTTPException(status_code=500, detail=f"Error loading results: {str(e)}")
    
    print(f"[DEBUG] Returning results for job {job_id}")
    return job_results[job_id]


@router.get("/export/{job_id}")
async def export_results(
    job_id: str,
    format: Optional[str] = Query("json", enum=["json", "md"])
):
    """Export results as JSON or Markdown file."""
    try:
        results = storage.get_results(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Results not found")
    
    job_dir = Path(settings.output_dir) / job_id
    
    if format == "md":
        file_path = job_dir / "report.md"
        media_type = "text/markdown"
    else:
        file_path = job_dir / "full_report.json"
        media_type = "application/json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"mia_report_{job_id}.{format}"
    )
