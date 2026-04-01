"""
EduPath AI — Quiz API
Adaptive quiz generation, submission, and scoring.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from environment.student import student_manager
from environment.models import QuizResult, QuizDifficulty
from environment.curriculum import TOPIC_GRAPH
from ai.quiz_generator import generate_quiz, score_quiz

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class QuizRequest(BaseModel):
    student_id: str
    topic_id: str
    difficulty: str = "medium"
    num_questions: int = 5


class QuizSubmission(BaseModel):
    student_id: str
    topic_id: str
    questions: list  # The original questions
    answers: List[int]  # User's selected option indices


@router.post("/generate")
async def generate_topic_quiz(data: QuizRequest):
    """Generate a quiz for a specific topic."""
    # Fuzzy match the topic ID
    topic = TOPIC_GRAPH.get(data.topic_id)
    if not topic:
        normalized = data.topic_id.lower().replace(" ", "_").replace("-", "_")
        topic = TOPIC_GRAPH.get(normalized)
    if not topic:
        normalized = data.topic_id.lower().replace(" ", "_").replace("-", "_")
        for tid, t in TOPIC_GRAPH.items():
            if normalized in tid or tid in normalized or normalized.replace("_", " ") in t.name.lower():
                topic = t
                break
    topic_name = topic.name if topic else data.topic_id.replace("_", " ").title()

    quiz = generate_quiz(topic_name, data.difficulty, data.num_questions)

    return {
        "topic_id": data.topic_id,
        "topic_name": topic_name,
        "difficulty": data.difficulty,
        "questions": quiz.get("questions", []),
    }


@router.post("/submit")
async def submit_quiz(data: QuizSubmission):
    """Submit quiz answers and get adaptive feedback."""
    student = student_manager.get(data.student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    # Score the quiz
    result = score_quiz(data.questions, data.answers)

    # Record in student history
    quiz_result = QuizResult(
        topic_id=data.topic_id,
        score=result["score"],
        total_questions=result["total_questions"],
        correct_answers=result["correct_answers"],
        passed=result["passed"],
        difficulty=QuizDifficulty.MEDIUM,
    )
    student_manager.record_quiz(data.student_id, quiz_result)

    # Get adaptive recommendation
    if result["recommendation"] == "restart_topic":
        topic = TOPIC_GRAPH.get(data.topic_id)
        if topic and topic.resources:
            result["alternative_resources"] = [
                {"title": r.title, "type": r.type.value, "url": r.url}
                for r in topic.resources[:3]
            ]

    return result


@router.get("/history/{student_id}")
async def get_quiz_history(student_id: str):
    """Get quiz history for a student."""
    student = student_manager.get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    return {
        "quiz_history": [q.model_dump() for q in student.quiz_history],
        "quiz_streak": student.quiz_streak,
        "total_quizzes": len(student.quiz_history),
        "pass_rate": round(
            sum(1 for q in student.quiz_history if q.passed) / max(len(student.quiz_history), 1) * 100, 1
        )
    }
