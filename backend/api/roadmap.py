"""
EduPath AI — Roadmap API
Generate and retrieve personalized learning roadmaps.
Syncs to Supabase for persistence.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os

from environment.student import student_manager
from ai.roadmap_generator import generate_roadmap

router = APIRouter(prefix="/api/roadmap", tags=["roadmap"])

# Store roadmaps in data directory (local cache)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class RoadmapRequest(BaseModel):
    student_id: str
    force_regenerate: bool = False


@router.post("/generate")
async def generate_student_roadmap(data: RoadmapRequest):
    """Generate a personalized learning roadmap for the student."""
    student = student_manager.get(data.student_id)
    if not student:
        raise HTTPException(404, "Student not found. Complete onboarding first.")

    # Check for cached roadmap (local first, then Supabase)
    roadmap_file = os.path.join(DATA_DIR, f"roadmap_{data.student_id}.json")
    if not data.force_regenerate:
        # Try local cache
        if os.path.exists(roadmap_file):
            with open(roadmap_file, "r") as f:
                return json.load(f)
        # Try Supabase
        try:
            from db.supabase_client import get_roadmap as sb_get_roadmap
            sb_roadmap = sb_get_roadmap(data.student_id)
            if sb_roadmap:
                # Save to local cache too
                with open(roadmap_file, "w") as f:
                    json.dump(sb_roadmap, f, indent=2)
                return sb_roadmap
        except Exception:
            pass

    # Build skill levels dict
    skill_levels = {}
    for s in student.self_assessed_skills:
        skill_levels[s.skill] = s.level

    current_skills = student.resume_skills + [s.skill for s in student.self_assessed_skills]

    roadmap = generate_roadmap(
        target_field=student.target_field or "tech",
        learning_goal=student.learning_goal,
        current_skills=current_skills,
        skill_levels=skill_levels,
        jd_skills=student.jd_required_skills,
        weekly_hours=student.weekly_hours,
        duration_weeks=max(8, 52 // max(student.weekly_hours // 5, 1)),
    )

    # Cache locally
    with open(roadmap_file, "w") as f:
        json.dump(roadmap, f, indent=2)

    # Sync to Supabase
    try:
        from db.supabase_client import save_roadmap
        save_roadmap(data.student_id, roadmap)
    except Exception:
        pass

    return roadmap


@router.get("/{student_id}")
async def get_roadmap(student_id: str):
    """Get the cached roadmap for a student."""
    # Try local cache
    roadmap_file = os.path.join(DATA_DIR, f"roadmap_{student_id}.json")
    if os.path.exists(roadmap_file):
        with open(roadmap_file, "r") as f:
            return json.load(f)

    # Try Supabase
    try:
        from db.supabase_client import get_roadmap as sb_get_roadmap
        sb_roadmap = sb_get_roadmap(student_id)
        if sb_roadmap:
            return sb_roadmap
    except Exception:
        pass

    raise HTTPException(404, "Roadmap not found. Generate one first.")
