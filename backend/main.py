import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from shared.config import get_settings


settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Ossiemate AI Lab - Microsoft Foundry "
        "and AI-103 practical demonstrations."
    ),
    docs_url="/docs",
    redoc_url="/redoc"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"]
)


EXERCISES = [
    {
        "id": "03",
        "name": "Conversational AI",
        "description": (
            "Responses API, streaming, asynchronous "
            "execution and concurrency."
        ),
        "status": "integration_pending",
        "features": [
            "Chat responses",
            "Conversation continuity",
            "Streaming",
            "Async execution",
            "Concurrency benchmarking"
        ]
    },
    {
        "id": "04",
        "name": "File and Web Search",
        "description": (
            "Grounded AI responses using uploaded "
            "documents and web search."
        ),
        "status": "integration_pending",
        "features": [
            "Vector stores",
            "File search",
            "Web search",
            "Tool execution tracking"
        ]
    },
    {
        "id": "05",
        "name": "Model Fine-tuning",
        "description": (
            "Training datasets, fine-tuning jobs "
            "and model comparison."
        ),
        "status": "integration_pending",
        "features": [
            "Training data preparation",
            "Fine-tuning job management",
            "Model deployment",
            "Model comparison"
        ]
    },
    {
        "id": "06",
        "name": "Responsible AI",
        "description": (
            "Content filtering, guardrails "
            "and AI safety evaluation."
        ),
        "status": "integration_pending",
        "features": [
            "Content filtering",
            "Guardrail configuration",
            "Safety testing",
            "Evaluation results"
        ]
    }
]


EXERCISES.extend(json.loads(Path(__file__).with_name('expansion_catalog.json').read_text(encoding='utf-8')))

@app.get("/")
def root():

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "message": "Welcome to Ossiemate AI Lab",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "ossiemate-ai-lab-backend",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


@app.get("/api/info")
def application_info():

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "model": settings.model_deployment,
        "exercise_count": len(EXERCISES),
        "live_ai_enabled": False
    }


@app.get("/api/exercises")
def get_exercises():

    return {
        "total": len(EXERCISES),
        "exercises": EXERCISES
    }


from routers.protected import router as protected_router

app.include_router(protected_router)

from routers.exercises import router as exercise_router
app.include_router(exercise_router)
