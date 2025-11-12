"""API endpoints for model management and configuration."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.models.model_manager import model_manager
from app.config.settings import settings

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelConfig(BaseModel):
    """Model configuration request."""
    step: str
    provider: str
    model: str
    fallback: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information response."""
    step: str
    provider: str
    model: str
    fallback: Optional[str]
    status: str
    error: Optional[str] = None


@router.get("/status")
async def get_models_status() -> Dict[str, Any]:
    """Get status of all configured models."""
    try:
        health_check = model_manager.health_check()
        return {
            "status": "success",
            "models": health_check,
            "pipeline_version": "2.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check model status: {str(e)}")


@router.get("/available/{step}")
async def get_available_models(step: str) -> Dict[str, List[str]]:
    """Get available models for a specific step."""
    try:
        available = model_manager.get_available_models(step)
        return available
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available models: {str(e)}")


@router.get("/config")
async def get_current_config() -> Dict[str, Dict[str, str]]:
    """Get current model configuration."""
    return settings.models


@router.post("/config")
async def update_model_config(config: ModelConfig) -> Dict[str, str]:
    """Update model configuration for a specific step."""
    try:
        model_manager.update_model_config(
            config.step,
            config.provider,
            config.model,
            config.fallback
        )
        
        return {
            "status": "success",
            "message": f"Updated {config.step} model to {config.provider}/{config.model}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update model config: {str(e)}")


@router.post("/test/{step}")
async def test_model_step(step: str) -> Dict[str, Any]:
    """Test a specific model step."""
    try:
        # Try to load the model for the step
        model = model_manager.get_model_for_step(step)
        
        # Basic test based on step type
        test_result = await _test_model_functionality(step, model)
        
        return {
            "status": "success",
            "step": step,
            "test_result": test_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model test failed: {str(e)}")


@router.get("/capabilities")
async def get_pipeline_capabilities() -> Dict[str, Any]:
    """Get current pipeline capabilities."""
    try:
        from app.preprocessing.enhanced_pipeline import enhanced_pipeline
        return enhanced_pipeline.get_pipeline_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")


async def _test_model_functionality(step: str, model: Any) -> Dict[str, Any]:
    """Test basic functionality of a model step."""
    test_text = "This is a test meeting transcript. John will send the report by Friday."
    
    try:
        if step == "summarization":
            if hasattr(model, 'summarize'):
                result = model.summarize(test_text, max_length=50)
                return {"type": "summarization", "input_length": len(test_text), "output_length": len(result)}
        
        elif step == "embedding":
            if hasattr(model, 'encode'):
                embeddings = model.encode([test_text])
                return {"type": "embedding", "embedding_shape": list(embeddings.shape) if hasattr(embeddings, 'shape') else "unknown"}
        
        elif step == "punctuation":
            if hasattr(model, 'restore_punctuation'):
                result = model.restore_punctuation("this is a test without punctuation")
                return {"type": "punctuation", "restored": result}
        
        elif step == "diarization":
            if hasattr(model, 'normalize_speakers'):
                return {"type": "diarization", "method": "text_based"}
            elif hasattr(model, 'diarize_audio'):
                return {"type": "diarization", "method": "audio_based"}
        
        return {"type": step, "status": "loaded", "method": "unknown"}
        
    except Exception as e:
        return {"type": step, "status": "error", "error": str(e)}