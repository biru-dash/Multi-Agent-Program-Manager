"""FastAPI routes for Meeting Intelligence Agent."""
import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
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

# Meeting transcripts folder path (relative to backend directory)
MEETING_TRANSCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "meeting_transcripts"
MEETING_TRANSCRIPTS_DIR.mkdir(exist_ok=True)


class ProcessRequest(BaseModel):
    """Request model for processing."""
    model_strategy: Optional[str] = "hybrid"
    preprocessing: Optional[str] = "advanced"


@router.get("/transcripts")
async def list_transcripts():
    """List available transcript files from meeting_transcripts folder."""
    try:
        transcript_files = []
        allowed_extensions = {'.txt', '.json', '.srt'}
        
        if not MEETING_TRANSCRIPTS_DIR.exists():
            return {"files": []}
        
        for file_path in MEETING_TRANSCRIPTS_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                file_size = file_path.stat().st_size
                transcript_files.append({
                    "filename": file_path.name,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "path": str(file_path.relative_to(MEETING_TRANSCRIPTS_DIR.parent))
                })
        
        # Sort by filename
        transcript_files.sort(key=lambda x: x["filename"])
        
        return {"files": transcript_files}
    except Exception as e:
        print(f"Error listing transcripts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error listing transcripts: {str(e)}")


@router.post("/transcripts/select")
async def select_transcript(filename: str = Query(...)):
    """Select a transcript file from meeting_transcripts folder and prepare it for processing."""
    try:
        file_path = MEETING_TRANSCRIPTS_DIR / filename
        
        # Security check: ensure file is within the allowed directory
        if not file_path.exists() or not str(file_path).startswith(str(MEETING_TRANSCRIPTS_DIR)):
            raise HTTPException(status_code=404, detail=f"Transcript file '{filename}' not found")
        
        # Validate file extension
        allowed_extensions = {'.txt', '.json', '.srt'}
        if file_path.suffix.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
            )
        
        # Read file and create upload_id (reuse existing storage mechanism)
        with open(file_path, 'rb') as f:
            contents = f.read()
        
        upload_id = storage.save_upload(contents, filename)
        
        return {
            "upload_id": upload_id,
            "filename": filename,
            "size_mb": round(file_size_mb, 2),
            "source": "meeting_transcripts"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error selecting transcript: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error selecting transcript: {str(e)}")


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
    # Persist initial status to disk
    storage.save_job_status(job_id, job_status[job_id])
    
    # Run processing in background
    asyncio.create_task(process_job(job_id, upload_id, model_strategy, preprocessing))
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Processing started. Poll /api/status/{job_id} for updates."
    }


def _update_job_status(job_id: str, updates: Dict[str, Any]):
    """Update job status in memory and persist to disk."""
    if job_id not in job_status:
        job_status[job_id] = {}
    job_status[job_id].update(updates)
    # Persist to disk for recovery after server reload
    storage.save_job_status(job_id, job_status[job_id])


async def process_job(job_id: str, upload_id: str, model_strategy: str, preprocessing: str):
    """Background job processor."""
    try:
        _update_job_status(job_id, {"progress": 10, "message": "Loading transcript..."})
        
        # Get file path
        file_path = storage.get_upload_path(upload_id)
        
        # Parse transcript
        segments = TranscriptParser.parse(str(file_path))
        
        _update_job_status(job_id, {"progress": 30, "message": "Preprocessing transcript..."})
        
        # Preprocess
        advanced = preprocessing == "advanced"
        cleaner = get_cleaner()
        processed_segments, preprocess_metadata = cleaner.process(
            segments,
            remove_fillers=advanced,
            normalize_speakers=advanced,
            segment_topics=advanced,
            remove_small_talk=advanced,
            merge_short_turns=advanced
        )
        
        _update_job_status(job_id, {"progress": 50, "message": "Initializing models..."})
        
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
        
        _update_job_status(job_id, {"progress": 60, "message": "Extracting meeting intelligence..."})
        
        # Extract information
        extractor = MeetingExtractor(model_adapter, cleaner)
        results = extractor.process(processed_segments)
        
        # Check quality and potentially fallback to remote API if using local strategy
        if model_strategy == "local" and results.get("quality_warning", False):
            _update_job_status(job_id, {
                "progress": 70,
                "message": "Quality check: Low quality detected. Attempting fallback to remote API..."
            })
            
            # Try fallback to remote API for summarization only
            try:
                from app.models.adapter import HuggingFaceInferenceAdapter
                if settings.huggingface_token:
                    remote_adapter = HuggingFaceInferenceAdapter(settings.huggingface_token)
                    # Create a hybrid extractor with remote summarization
                    hybrid_extractor = MeetingExtractor(remote_adapter, cleaner)
                    # Re-extract summary with remote API
                    new_summary = hybrid_extractor.extract_summary(processed_segments)
                    if new_summary and len(new_summary) > len(results.get("summary", "")):
                        # Update results with better summary and re-extract
                        new_structured = hybrid_extractor.extract_structured_data(new_summary, processed_segments)
                        results["summary"] = new_summary
                        results["decisions"] = new_structured["decisions"]
                        results["action_items"] = new_structured["action_items"]
                        results["risks"] = new_structured["risks"]
                        # Recalculate quality metrics
                        results["quality_metrics"] = hybrid_extractor._calculate_quality_metrics(new_summary, new_structured)
                        results["quality_warning"] = False
                        results["used_fallback"] = True
                        _update_job_status(job_id, {
                            "progress": 75,
                            "message": "Fallback to remote API improved results."
                        })
            except Exception as fallback_error:
                print(f"Warning: Fallback to remote API failed: {fallback_error}")
                results["fallback_error"] = str(fallback_error)
                # Continue with original results
        
        _update_job_status(job_id, {"progress": 80, "message": "Saving results..."})
        
        # Add preprocessing metadata
        results["preprocessing_metadata"] = preprocess_metadata
        
        # Save results
        try:
            storage.save_results(job_id, results)
            job_results[job_id] = results
            _update_job_status(job_id, {
                "progress": 100,
                "status": "completed",
                "message": "Processing complete!"
            })
        except Exception as save_error:
            # Even if save fails, try to keep results in memory
            job_results[job_id] = results
            _update_job_status(job_id, {
                "progress": 95,
                "status": "completed",
                "message": f"Processing complete (save warning: {str(save_error)})"
            })
            print(f"Warning: Could not save results to disk for job {job_id}: {save_error}")
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"ERROR processing job {job_id}:")
        print(f"{'='*60}")
        print(error_trace)
        print(f"{'='*60}\n")
        
        _update_job_status(job_id, {
            "status": "failed",
            "message": f"Error: {str(e)}",
            "error": str(e),
            "traceback": error_trace,
            "progress": 0
        })


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status."""
    if job_id not in job_status:
        # Try loading from disk (in case server was reloaded)
        disk_status = storage.get_job_status(job_id)
        if disk_status:
            job_status[job_id] = disk_status
            # Also try to load results if available
            try:
                results = storage.get_results(job_id)
                job_results[job_id] = results
            except FileNotFoundError:
                pass
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load results due to JSON error: {e}")
                # Continue without results - status is still valid
            except Exception as e:
                print(f"Warning: Could not load results: {e}")
            return disk_status
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
