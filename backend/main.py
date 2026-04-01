"""
EduPath AI — FastAPI Application Entry Point
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.onboarding import router as onboarding_router
from api.roadmap import router as roadmap_router
from api.quiz import router as quiz_router
from api.badges import router as badges_router
from api.career import router as career_router
from api.resources import router as resources_router
from api.projects import router as projects_router
from environment.curriculum import TOPIC_GRAPH, PROJECT_DB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="EduPath AI",
    description="Personalized Learning Tutor Environment — OpenEnv Compliant",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(onboarding_router)
app.include_router(roadmap_router)
app.include_router(quiz_router)
app.include_router(badges_router)
app.include_router(career_router)
app.include_router(resources_router)
app.include_router(projects_router)


@app.get("/")
async def root():
    return {
        "name": "EduPath AI",
        "version": "1.0.0",
        "description": "Personalized Learning Tutor Environment",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/topics")
async def get_all_topics():
    """Get all available topics."""
    return {
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "field": t.field,
                "prerequisites": t.prerequisites,
                "difficulty": t.difficulty,
                "estimated_hours": t.estimated_hours,
            }
            for t in TOPIC_GRAPH.values()
        ],
        "total": len(TOPIC_GRAPH),
    }


@app.get("/api/topics/{field}")
async def get_topics_by_field(field: str):
    """Get topics filtered by field."""
    from environment.curriculum import get_topics_for_field
    topics = get_topics_for_field(field)
    return {
        "field": field,
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "field": t.field,
                "prerequisites": t.prerequisites,
                "difficulty": t.difficulty,
                "estimated_hours": t.estimated_hours,
                "resources": [{"title": r.title, "type": r.type.value, "url": r.url} for r in t.resources[:3]],
            }
            for t in topics
        ],
        "total": len(topics),
    }


@app.get("/api/env/info")
async def get_env_info():
    """Get environment info (OpenEnv metadata)."""
    return {
        "name": "EduPath AI",
        "version": "1.0.0",
        "description": "Personalized AI tutor RL environment",
        "fields_supported": ["tech", "healthcare", "business", "law", "design"],
        "total_topics": len(TOPIC_GRAPH),
        "total_projects": len(PROJECT_DB),
        "actions": [
            "recommend_topic", "assign_quiz", "assign_mini_project",
            "assign_capstone", "recommend_resource", "suggest_event_or_hackathon",
            "mark_job_ready"
        ],
        "api_key_configured": bool(os.getenv("API_BASE_URL")),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
