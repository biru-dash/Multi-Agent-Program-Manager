"""API routes for evaluation and human review."""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.config.settings import settings
from app.evaluation.evaluation_runner import EvaluationRunner
from app.evaluation.model_adapter import get_evaluation_model_info
from app.utils.storage import StorageManager

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

# Initialize components
evaluation_runner = EvaluationRunner()
storage = StorageManager(
    output_dir=settings.output_dir,
    upload_dir=settings.upload_dir
)

# In-memory storage for evaluations (production: use database)
evaluation_results = {}
human_reviews = {}


class HumanReviewRequest(BaseModel):
    """Human review submission model."""
    job_id: str
    component: str
    scores: Dict[str, float]
    explanations: Dict[str, str]
    overall_feedback: Optional[str] = None
    reviewer_id: Optional[str] = None
    mark_for_retraining: bool = False


class EvaluationTriggerRequest(BaseModel):
    """Request to trigger evaluation for a job."""
    include_llm: bool = True
    include_metrics: bool = True
    reference_data: Optional[Dict[str, Any]] = None


@router.post("/{job_id}/trigger")
async def trigger_evaluation(
    job_id: str,
    request: EvaluationTriggerRequest = Body(...)
):
    """Trigger automated evaluation for a completed extraction job."""
    try:
        # Load extraction results
        extraction_results = storage.get_results(job_id)
        
        # For now, use a placeholder transcript
        # In production, store transcript with job
        transcript = "Transcript would be loaded from storage"
        
        # Run evaluation in background
        asyncio.create_task(
            _run_evaluation_async(
                job_id,
                transcript,
                extraction_results,
                request.reference_data
            )
        )
        
        return {
            "message": "Evaluation triggered",
            "job_id": job_id,
            "status": "running"
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_evaluation_async(
    job_id: str,
    transcript: str,
    extraction_results: Dict[str, Any],
    reference_data: Optional[Dict[str, Any]]
):
    """Run evaluation asynchronously."""
    try:
        results = await evaluation_runner.run_evaluation(
            job_id,
            transcript,
            extraction_results,
            reference_data
        )
        evaluation_results[job_id] = results
    except Exception as e:
        print(f"Error in async evaluation: {e}")
        evaluation_results[job_id] = {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/{job_id}/status")
async def get_evaluation_status(job_id: str):
    """Get evaluation status and results."""
    if job_id not in evaluation_results:
        # Try loading from disk
        try:
            results = storage.get_results(job_id)
            # Check if evaluation exists
            eval_path = storage.output_dir / job_id / "evaluation" / "evaluation_results.json"
            if eval_path.exists():
                import json
                with open(eval_path, 'r') as f:
                    evaluation_results[job_id] = json.load(f)
            else:
                raise HTTPException(status_code=404, detail="Evaluation not found")
        except:
            raise HTTPException(status_code=404, detail="Evaluation not found")
            
    return evaluation_results[job_id]


@router.post("/{job_id}/human-review")
async def submit_human_review(
    job_id: str,
    review: HumanReviewRequest
):
    """Submit human review scores for an extraction."""
    # Validate job exists
    try:
        extraction_results = storage.get_results(job_id)
    except:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
    # Validate component
    if review.component not in ['summary', 'decisions', 'action_items', 'risks']:
        raise HTTPException(status_code=400, detail="Invalid component")
        
    # Store review
    review_id = f"{job_id}_{review.component}_{datetime.utcnow().timestamp()}"
    
    review_data = {
        "review_id": review_id,
        "job_id": job_id,
        "component": review.component,
        "scores": review.scores,
        "explanations": review.explanations,
        "overall_feedback": review.overall_feedback,
        "reviewer_id": review.reviewer_id or "anonymous",
        "timestamp": datetime.utcnow().isoformat(),
        "mark_for_retraining": review.mark_for_retraining
    }
    
    # Store in memory and disk
    if job_id not in human_reviews:
        human_reviews[job_id] = {}
    human_reviews[job_id][review.component] = review_data
    
    # Save to disk
    _save_human_review(job_id, review_data)
    
    # Trigger re-aggregation if evaluation exists
    if job_id in evaluation_results:
        asyncio.create_task(_reaggregate_with_human_review(job_id))
        
    return {
        "message": "Review submitted successfully",
        "review_id": review_id
    }


def _save_human_review(job_id: str, review_data: Dict[str, Any]):
    """Save human review to disk."""
    from pathlib import Path
    import json
    
    review_dir = Path(settings.output_dir) / job_id / "evaluation" / "human_reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    
    review_file = review_dir / f"{review_data['component']}_review.json"
    with open(review_file, 'w') as f:
        json.dump(review_data, f, indent=2)


async def _reaggregate_with_human_review(job_id: str):
    """Re-aggregate evaluation with human review."""
    try:
        # Get existing evaluations
        eval_data = evaluation_results.get(job_id, {})
        llm_eval = eval_data.get('llm_evaluation')
        metrics_eval = eval_data.get('metrics_evaluation')
        
        # Format human reviews
        human_eval = {
            'evaluations': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for component, review in human_reviews.get(job_id, {}).items():
            human_eval['evaluations'][component] = {
                'scores': review['scores'],
                'explanations': review['explanations'],
                'overall_score': sum(review['scores'].values()) / len(review['scores'])
            }
            
        # Re-aggregate
        aggregated = evaluation_runner.aggregator.aggregate_evaluations(
            llm_eval=llm_eval,
            human_eval=human_eval if human_eval['evaluations'] else None,
            metrics_eval=metrics_eval
        )
        
        # Update results
        evaluation_results[job_id]['human_evaluation'] = human_eval
        evaluation_results[job_id]['aggregated_evaluation'] = aggregated
        
        # Regenerate improvement report
        extraction_results = storage.get_results(job_id)
        improvement_report = evaluation_runner.aggregator.generate_improvement_report(
            aggregated,
            extraction_results
        )
        evaluation_results[job_id]['improvement_report'] = improvement_report
        
        # Save updated results
        evaluation_runner._save_evaluation_results(job_id, evaluation_results[job_id])
        
    except Exception as e:
        print(f"Error re-aggregating evaluation: {e}")


@router.get("/{job_id}/human-reviews")
async def get_human_reviews(job_id: str):
    """Get all human reviews for a job."""
    reviews = human_reviews.get(job_id, {})
    
    if not reviews:
        # Try loading from disk
        from pathlib import Path
        import json
        
        review_dir = Path(settings.output_dir) / job_id / "evaluation" / "human_reviews"
        if review_dir.exists():
            for review_file in review_dir.glob("*_review.json"):
                with open(review_file, 'r') as f:
                    review_data = json.load(f)
                    component = review_data['component']
                    if job_id not in human_reviews:
                        human_reviews[job_id] = {}
                    human_reviews[job_id][component] = review_data
                    
            reviews = human_reviews.get(job_id, {})
            
    return {
        "job_id": job_id,
        "reviews": list(reviews.values()),
        "components_reviewed": list(reviews.keys())
    }


@router.get("/schema")
async def get_evaluation_schema():
    """Get the evaluation schema for frontend."""
    from pathlib import Path
    import json
    
    schema_path = Path(__file__).parent.parent / "config" / "evaluation_schema.json"
    with open(schema_path, 'r') as f:
        schema = json.load(f)
        
    return schema


@router.get("/model-info")
async def get_model_info():
    """Get information about the current evaluation model configuration."""
    return get_evaluation_model_info()


@router.get("/jobs/{status}")
async def list_evaluation_jobs(
    status: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List evaluation jobs by status."""
    jobs = []
    
    # Filter by status
    for job_id, eval_data in evaluation_results.items():
        if status == "all" or eval_data.get('status') == status:
            jobs.append({
                "job_id": job_id,
                "status": eval_data.get('status'),
                "timestamp": eval_data.get('timestamp'),
                "aggregate_score": eval_data.get('aggregated_evaluation', {}).get('aggregate_score'),
                "has_human_review": job_id in human_reviews
            })
            
    # Sort by timestamp (newest first)
    jobs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Paginate
    total = len(jobs)
    jobs = jobs[offset:offset + limit]
    
    return {
        "jobs": jobs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/batch")
async def trigger_batch_evaluation(
    job_ids: List[str] = Body(...),
    parallel: bool = Query(True)
):
    """Trigger evaluation for multiple jobs."""
    # Validate all jobs exist
    missing_jobs = []
    for job_id in job_ids:
        try:
            storage.get_results(job_id)
        except:
            missing_jobs.append(job_id)
            
    if missing_jobs:
        raise HTTPException(
            status_code=400,
            detail=f"Jobs not found: {', '.join(missing_jobs)}"
        )
        
    # Run batch evaluation
    asyncio.create_task(
        evaluation_runner.run_batch_evaluation(job_ids, parallel)
    )
    
    return {
        "message": f"Batch evaluation triggered for {len(job_ids)} jobs",
        "job_ids": job_ids,
        "parallel": parallel
    }


@router.get("/retraining-candidates")
async def get_retraining_candidates():
    """Get extractions marked for retraining."""
    candidates = []
    
    for job_id, job_reviews in human_reviews.items():
        for component, review in job_reviews.items():
            if review.get('mark_for_retraining'):
                candidates.append({
                    "job_id": job_id,
                    "component": component,
                    "reviewer_id": review.get('reviewer_id'),
                    "timestamp": review.get('timestamp'),
                    "scores": review.get('scores'),
                    "feedback": review.get('overall_feedback')
                })
                
    return {
        "candidates": candidates,
        "total": len(candidates)
    }