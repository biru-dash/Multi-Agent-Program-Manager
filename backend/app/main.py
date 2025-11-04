"""FastAPI application entry point for Meeting Intelligence Agent."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config.settings import settings

app = FastAPI(
    title="Meeting Intelligence Agent API",
    description="API for extracting structured insights from meeting transcripts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (default)
        "http://localhost:3000",  # Alternative React dev server
        "http://localhost:8080",  # Vite custom port
        "http://localhost:8081",  # Vite alternative port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",  # Frontend port
        "http://[::1]:5173",  # IPv6 localhost
        "http://[::1]:8080",
        "http://[::1]:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Meeting Intelligence Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_strategy": settings.model_strategy
    }
