"""
EduPath AI — Badges API
Badge management and achievement tracking.
"""
from fastapi import APIRouter, HTTPException

from environment.student import student_manager

router = APIRouter(prefix="/api/badges", tags=["badges"])


# Badge definitions with criteria
BADGE_CATALOG = [
    {"id": "topics_5", "name": "Explorer Badge", "description": "Complete 5 topics", "icon": "📚", "criteria": "5 topics completed", "type": "topic_completion"},
    {"id": "topics_10", "name": "Scholar Badge", "description": "Complete 10 topics", "icon": "📚", "criteria": "10 topics completed", "type": "topic_completion"},
    {"id": "topics_15", "name": "Expert Badge", "description": "Complete 15 topics", "icon": "📚", "criteria": "15 topics completed", "type": "topic_completion"},
    {"id": "streak_3", "name": "Hat Trick Streak", "description": "Pass 3 quizzes in a row", "icon": "🔥", "criteria": "3 quiz streak", "type": "quiz_streak"},
    {"id": "streak_5", "name": "On Fire Streak", "description": "Pass 5 quizzes in a row", "icon": "🔥", "criteria": "5 quiz streak", "type": "quiz_streak"},
    {"id": "streak_10", "name": "Unstoppable Streak", "description": "Pass 10 quizzes in a row", "icon": "🔥", "criteria": "10 quiz streak", "type": "quiz_streak"},
    {"id": "projects_1", "name": "Builder Badge", "description": "Complete your first project", "icon": "🛠️", "criteria": "1 project completed", "type": "project_success"},
    {"id": "projects_3", "name": "Creator Badge", "description": "Complete 3 projects", "icon": "🛠️", "criteria": "3 projects completed", "type": "project_success"},
    {"id": "projects_5", "name": "Architect Badge", "description": "Complete 5 projects", "icon": "🛠️", "criteria": "5 projects completed", "type": "project_success"},
    {"id": "job_ready", "name": "Job Ready!", "description": "Achieve 80%+ job readiness score", "icon": "💼", "criteria": "80% job readiness", "type": "job_ready"},
]


@router.get("/catalog")
async def get_badge_catalog():
    """Get all available badges with criteria."""
    return {"badges": BADGE_CATALOG}


@router.get("/{student_id}")
async def get_student_badges(student_id: str):
    """Get badges earned by a student."""
    student = student_manager.get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    earned_ids = {b.id for b in student.badges}

    # Combine catalog with earned status
    badge_status = []
    for badge in BADGE_CATALOG:
        badge_status.append({
            **badge,
            "earned": badge["id"] in earned_ids,
        })

    return {
        "earned_count": len(student.badges),
        "total_count": len(BADGE_CATALOG),
        "badges": badge_status,
    }
