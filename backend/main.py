"""
EduPath AI — FastAPI Application Entry Point
Team KRIYA | Meta Hackathon 2026

Serves the OpenEnv-compliant RL environment API (/reset, /step, /state, /grade)
alongside the student-facing REST API for onboarding, quizzes, projects,
badges, career readiness, and resource discovery.
"""
import os
import random
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.onboarding import router as onboarding_router
from api.roadmap import router as roadmap_router
from api.quiz import router as quiz_router
from api.badges import router as badges_router
from api.career import router as career_router
from api.resources import router as resources_router
from api.projects import router as projects_router
from api.profile import router as profile_router
from environment.curriculum import TOPIC_GRAPH, PROJECT_DB
from environment.env import EduPathEnv
from environment.models import Action, ActionType, QuizDifficulty
from environment.student import student_manager
from environment.graders import grade_task1, grade_task2, grade_task3

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
app.include_router(profile_router)


# ═══ OpenEnv Session Management ═══
env_sessions: Dict[str, EduPathEnv] = {}
DEFAULT_SESSION = "default"


class ResetRequest(BaseModel):
    """Request body for /reset endpoint."""
    student_id: Optional[str] = None
    task_id: Optional[str] = None
    student_profile: Optional[Dict[str, Any]] = None
    seed: Optional[int] = 42


class StepRequest(BaseModel):
    """Request body for /step endpoint."""
    type: str = "recommend_topic"
    topic_id: Optional[str] = None
    project_id: Optional[str] = None
    difficulty: Optional[str] = None
    session_id: Optional[str] = None


class StateRequest(BaseModel):
    """Request body for /state endpoint."""
    session_id: Optional[str] = None


class GradeRequest(BaseModel):
    """Request body for /grade endpoint."""
    task_id: str
    session_id: Optional[str] = None


# ═══ OpenEnv Core Endpoints (REQUIRED by spec) ═══

@app.post("/reset")
async def env_reset(request: ResetRequest = None):
    """
    OpenEnv reset() — Initialize or reset the environment.
    Returns the initial observation.
    """
    if request is None:
        request = ResetRequest()

    # Set seed for reproducibility
    if request.seed is not None:
        random.seed(request.seed)

    session_id = DEFAULT_SESSION

    # Clean up previous session's student data to prevent accumulation
    old_env = env_sessions.get(session_id)
    if old_env and old_env.student_id:
        # Remove old student from in-memory store (keeps disk clean)
        student_manager.students.pop(old_env.student_id, None)

    env = EduPathEnv()
    env_sessions[session_id] = env

    # If task-specific profile provided, create and configure student
    student_id = request.student_id
    if request.student_profile:
        profile = request.student_profile
        student = student_manager.create(name=profile.get("name", "Agent Student"))
        student_manager.update_from_onboarding(student.id, profile)
        student_id = student.id
    elif not student_id:
        student = student_manager.create(name="OpenEnv Agent")
        student_manager.update_from_onboarding(student.id, {
            "target_field": "tech",
            "learning_goal": "Learn Python and become a developer",
            "weekly_hours": 10,
        })
        student_id = student.id

    obs = env.reset(student_id)
    return {
        "observation": obs.model_dump(),
        "session_id": session_id,
        "info": {"student_id": student_id},
    }


@app.post("/step")
async def env_step(request: StepRequest):
    """
    OpenEnv step(action) — Execute an action in the environment.
    Returns observation, reward, done, info.
    """
    session_id = request.session_id or DEFAULT_SESSION
    env = env_sessions.get(session_id)
    if not env:
        return {
            "error": "No active session. Call /reset first.",
            "done": True,
        }

    # Build action from request
    try:
        action_type = ActionType(request.type)
    except ValueError:
        return {
            "error": f"Invalid action type: {request.type}",
            "valid_types": [t.value for t in ActionType],
        }

    difficulty = None
    if request.difficulty:
        try:
            difficulty = QuizDifficulty(request.difficulty)
        except ValueError:
            pass

    action = Action(
        type=action_type,
        topic_id=request.topic_id,
        project_id=request.project_id,
        difficulty=difficulty,
    )

    result = env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward.model_dump(),
        "done": result.done,
        "info": result.info,
    }


@app.post("/state")
async def env_state(request: StateRequest = None):
    """
    OpenEnv state() — Return current environment state.
    """
    if request is None:
        request = StateRequest()
    session_id = request.session_id or DEFAULT_SESSION
    env = env_sessions.get(session_id)
    if not env:
        return {
            "error": "No active session. Call /reset first.",
            "state": None,
        }
    return env.state()


@app.post("/grade")
async def env_grade(request: GradeRequest):
    """
    Grade the current session for a specific task.
    Returns a score between 0.0 and 1.0.
    """
    session_id = request.session_id or DEFAULT_SESSION
    env = env_sessions.get(session_id)
    if not env:
        return {"error": "No active session. Call /reset first.", "score": 0.0001}

    student = student_manager.get(env.student_id)
    if not student:
        return {"error": "Student not found.", "score": 0.0001}

    graders = {
        "task1_easy": lambda s: grade_task1(s),
        "task2_medium": lambda s: grade_task2(s),
        "task3_hard": lambda s: grade_task3(s),
    }
    # Import task4/task5 graders
    try:
        from environment.graders import grade_task4, grade_task5
        graders["task4_team"] = lambda s: grade_task4([s], steps_used=env.total_steps)
        graders["task5_deadline"] = lambda s: grade_task5(s, steps_used=env.total_steps)
    except ImportError:
        pass
    grader = graders.get(request.task_id)
    if not grader:
        return {"error": f"Unknown task: {request.task_id}", "score": 0.0001}

    score = grader(student)
    score = round(score, 4)
    # Ensure score falls strictly within (0, 1)
    if score <= 0.0:
        score = 0.0001
    elif score >= 1.0:
        score = 0.9999
        
    return {
        "task_id": request.task_id,
        "score": score,
        "student_id": env.student_id,
        "completed_topics": student.completed_topics,
        "job_readiness_score": student.job_readiness_score,
    }


# ═══ Existing API Endpoints ═══

@app.get("/")
async def root():
    return {
        "name": "EduPath AI",
        "version": "1.0.0",
        "description": "Personalized Learning Tutor Environment",
        "status": "running",
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "POST /state",
        },
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
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
