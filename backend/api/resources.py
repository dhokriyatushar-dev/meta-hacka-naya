"""
EduPath AI — Resources API
Endpoints for fetching topic resources, tracking link clicks, and marking topics complete.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from environment.models import (
    ResourceCard, TopicPageResponse, LinkClickRequest, MarkCompleteRequest
)
from environment.curriculum import TOPIC_GRAPH
from environment.student import student_manager
from ai.resource_fetcher import fetch_resources_async
from ai.roadmap_generator import generate_topic_summary

router = APIRouter(prefix="/resources", tags=["resources"])
logger = logging.getLogger(__name__)


@router.get("/{topic_id}", response_model=TopicPageResponse)
async def get_topic_resources(topic_id: str, student_id: str = ""):
    """
    Get resources and AI summary for a topic.
    Returns ResourceCard list + AI-generated topic summary.
    """
    topic = TOPIC_GRAPH.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")

    # Get student context for personalized summary
    student = student_manager.get(student_id) if student_id else None
    field = student.target_field if student else topic.field
    goal = student.learning_goal if student else f"Learn {topic.name}"

    # Fetch resources (cached, async)
    raw_resources = await fetch_resources_async(topic.name, topic_id)

    resources = [
        ResourceCard(
            title=r["title"],
            url=r["url"],
            source=r.get("source", "Other"),
            description=r.get("description", ""),
            duration_estimate=r.get("duration_estimate", "~2 hours"),
            resource_type=r.get("resource_type", "course"),
        )
        for r in raw_resources
    ]

    # Generate AI summary (cached)
    ai_summary = await generate_topic_summary(topic.name, field, goal)

    # Check student state
    can_mark_complete = False
    quiz_unlocked = False
    if student:
        can_mark_complete = topic_id in student.clicked_resource_links and \
                            len(student.clicked_resource_links[topic_id]) > 0
        quiz_unlocked = topic_id in student.topics_studied

    return TopicPageResponse(
        topic_id=topic_id,
        topic_name=topic.name,
        ai_summary=ai_summary,
        resources=resources,
        can_mark_complete=can_mark_complete,
        quiz_unlocked=quiz_unlocked,
    )


@router.post("/{topic_id}/link-clicked")
async def record_link_click(topic_id: str, body: LinkClickRequest):
    """
    Record that a student clicked a resource link.
    Unlocks the 'Mark as Complete' button.
    """
    topic = TOPIC_GRAPH.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")

    student = student_manager.get(body.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{body.student_id}' not found")

    is_first = student_manager.record_link_click(body.student_id, topic_id, body.resource_url)

    return {
        "can_mark_complete": True,
        "is_first_click": is_first,
        "topic_id": topic_id,
    }


@router.post("/{topic_id}/mark-complete")
async def mark_topic_complete(topic_id: str, body: MarkCompleteRequest):
    """
    Mark a topic as 'studied' (link clicked + student confirms).
    Only works if student has clicked at least one resource link.
    Returns 403 if no link was clicked.
    """
    topic = TOPIC_GRAPH.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")

    student = student_manager.get(body.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{body.student_id}' not found")

    success = student_manager.mark_topic_studied(body.student_id, topic_id)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Cannot mark complete: no resource link was clicked for this topic. "
                   "Please visit at least one course link first."
        )

    return {
        "quiz_unlocked": True,
        "topic_id": topic_id,
        "message": f"Topic '{topic.name}' marked as studied. Quiz is now unlocked!",
    }
