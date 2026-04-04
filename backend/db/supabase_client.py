"""
EduPath AI — Supabase Database Client
Syncs student data to Supabase PostgreSQL for persistence.
Falls back gracefully if Supabase is not configured.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_supabase_client = None
_supabase_checked = False


def _get_client():
    """Get Supabase client (lazy init). Caches result to avoid repeated warnings."""
    global _supabase_client, _supabase_checked
    if _supabase_checked:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Database sync disabled.")
        _supabase_checked = True
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized successfully.")
        _supabase_checked = True
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        _supabase_checked = True
        return None


def is_configured() -> bool:
    """Check if Supabase is configured."""
    return bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_KEY"))


# ── Student Operations ──

def upsert_student(student_data: dict) -> bool:
    """Insert or update a student profile in Supabase."""
    client = _get_client()
    if not client:
        return False

    try:
        # Prepare data for Supabase (convert non-serializable fields)
        db_data = {
            "id": student_data.get("id"),
            "name": student_data.get("name", ""),
            "email": student_data.get("email", ""),
            "target_field": student_data.get("target_field", "tech"),
            "learning_goal": student_data.get("learning_goal", ""),
            "job_description": student_data.get("job_description", ""),
            "weekly_hours": student_data.get("weekly_hours", 10),
            "job_readiness_score": student_data.get("job_readiness_score", 0.0),
            "quiz_streak": student_data.get("quiz_streak", 0),
            "resume_skills": json.dumps(student_data.get("resume_skills", [])),
            "self_assessed_skills": json.dumps(student_data.get("self_assessed_skills", [])),
            "jd_required_skills": json.dumps(student_data.get("jd_required_skills", [])),
            "completed_topics": json.dumps(student_data.get("completed_topics", [])),
            "completed_projects": json.dumps(student_data.get("completed_projects", [])),
            "topics_studied": json.dumps(student_data.get("topics_studied", [])),
            "clicked_resource_links": json.dumps(student_data.get("clicked_resource_links", {})),
            "badges": json.dumps(student_data.get("badges", [])),
            "onboarding_complete": True,
        }

        client.table("students").upsert(db_data).execute()
        logger.info(f"Student {db_data['id']} synced to Supabase.")
        return True
    except Exception as e:
        logger.error(f"Failed to sync student to Supabase: {e}")
        return False


def get_student(student_id: str) -> Optional[dict]:
    """Get a student profile from Supabase."""
    client = _get_client()
    if not client:
        return None

    try:
        result = client.table("students").select("*").eq("id", student_id).execute()
        if result.data and len(result.data) > 0:
            row = result.data[0]
            # Parse JSON fields back
            for field in ["resume_skills", "self_assessed_skills", "jd_required_skills",
                          "completed_topics", "completed_projects", "topics_studied",
                          "clicked_resource_links", "badges"]:
                if isinstance(row.get(field), str):
                    try:
                        row[field] = json.loads(row[field])
                    except Exception:
                        pass
            return row
        return None
    except Exception as e:
        logger.error(f"Failed to get student from Supabase: {e}")
        return None


# ── Quiz Operations ──

def save_quiz_result(student_id: str, quiz_data: dict) -> bool:
    """Save a quiz result to Supabase."""
    client = _get_client()
    if not client:
        return False

    try:
        db_data = {
            "student_id": student_id,
            "topic_id": quiz_data.get("topic_id", ""),
            "score": quiz_data.get("score", 0),
            "total_questions": quiz_data.get("total_questions", 0),
            "correct_answers": quiz_data.get("correct_answers", 0),
            "passed": quiz_data.get("passed", False),
            "difficulty": quiz_data.get("difficulty", "medium"),
        }
        client.table("student_quizzes").insert(db_data).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save quiz to Supabase: {e}")
        return False


# ── Project Operations ──

def save_project_report(report_data: dict) -> bool:
    """Save a project evaluation report to Supabase."""
    client = _get_client()
    if not client:
        return False

    try:
        db_data = {
            "id": report_data.get("project_id"),
            "student_id": report_data.get("student_id"),
            "project_title": report_data.get("project_title", ""),
            "project_type": report_data.get("project_type", "mini_project"),
            "submission_text": report_data.get("submission_text", ""),
            "score": report_data.get("evaluation", {}).get("score", 0),
            "grade": report_data.get("evaluation", {}).get("grade", "N/A"),
            "is_passing": report_data.get("evaluation", {}).get("is_passing", False),
            "evaluation_data": json.dumps(report_data.get("evaluation", {})),
        }
        client.table("student_projects").upsert(db_data).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save project to Supabase: {e}")
        return False


# ── Roadmap Operations ──

def save_roadmap(student_id: str, roadmap_data: dict) -> bool:
    """Save a roadmap to Supabase."""
    client = _get_client()
    if not client:
        return False

    try:
        db_data = {
            "student_id": student_id,
            "roadmap_data": json.dumps(roadmap_data),
        }
        client.table("student_roadmaps").upsert(db_data).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save roadmap to Supabase: {e}")
        return False


def get_roadmap(student_id: str) -> Optional[dict]:
    """Get a roadmap from Supabase."""
    client = _get_client()
    if not client:
        return None

    try:
        result = client.table("student_roadmaps").select("*").eq("student_id", student_id).execute()
        if result.data and len(result.data) > 0:
            data = result.data[0].get("roadmap_data")
            if isinstance(data, str):
                return json.loads(data)
            return data
        return None
    except Exception as e:
        logger.error(f"Failed to get roadmap from Supabase: {e}")
        return None
