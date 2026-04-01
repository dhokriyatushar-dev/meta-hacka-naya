"""
EduPath AI — AI Roadmap Generator
Generates personalized learning roadmaps and topic summaries via LLM.
"""
import os
import json
import hashlib
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from ai.llm_client import generate_json, generate_text, is_api_key_set

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SUMMARY_CACHE_FILE = os.path.join(DATA_DIR, "summary_cache.json")
_executor = ThreadPoolExecutor(max_workers=2)


def _load_summary_cache() -> dict:
    if os.path.exists(SUMMARY_CACHE_FILE):
        try:
            with open(SUMMARY_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_summary_cache(cache: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUMMARY_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _generate_summary_sync(topic_name: str, field: str, student_goal: str) -> str:
    """Synchronous summary generation using LLM."""
    if not is_api_key_set():
        return _fallback_summary(topic_name, field, student_goal)

    system_prompt = """You are an expert tutor. Write a 300-500 word explanation of the given topic.
Do NOT include links, markdown headers, or bullet points. Plain paragraphs only."""

    user_prompt = f"""Write a 300-500 word explanation of "{topic_name}" for a student in the {field} field whose goal is: {student_goal}.
- Start with why this topic matters for their goal
- Explain the core concept in plain English
- Give 1 concrete real-world example from their field
- End with what they'll be able to do after learning this"""

    try:
        return generate_text(system_prompt, user_prompt)
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")
        return _fallback_summary(topic_name, field, student_goal)


def _fallback_summary(topic_name: str, field: str, goal: str) -> str:
    """Generate a basic summary when LLM is unavailable."""
    return (
        f"{topic_name} is a foundational skill for anyone pursuing a career in {field}. "
        f"Understanding {topic_name} is critical to achieving your goal of '{goal}'. "
        f"This topic covers the core principles, practical applications, and hands-on techniques "
        f"that will form the backbone of your learning journey. "
        f"By mastering {topic_name}, you will be able to apply these concepts directly to real-world "
        f"{field} challenges, build projects that showcase your competence, and confidently "
        f"move on to more advanced topics in your roadmap. "
        f"Take time to explore the resources below, work through the examples, and complete "
        f"at least one practical exercise before marking this topic as complete."
    )


async def generate_topic_summary(topic_name: str, field: str, student_goal: str) -> str:
    """
    Generates a 300-500 word plain-English explanation of a topic
    tailored to the student's field and goal.
    Cached in backend/data/summary_cache.json.
    """
    # Build cache key
    goal_hash = hashlib.md5(student_goal.encode()).hexdigest()[:8]
    cache_key = f"{topic_name.lower().replace(' ', '_')}_{field}_{goal_hash}"

    # Check cache
    cache = _load_summary_cache()
    if cache_key in cache:
        return cache[cache_key]

    # Generate via LLM (sync, in executor)
    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(
        _executor,
        _generate_summary_sync,
        topic_name, field, student_goal,
    )

    # Save to cache
    cache[cache_key] = summary
    _save_summary_cache(cache)

    return summary


ROADMAP_SYSTEM_PROMPT = """
You are a backend service that outputs ONLY valid JSON.

STRICT SCHEMA ENFORCEMENT:
You must output a JSON object adhering to this EXACT schema:

{
  "domain": "string",
  "target_role": "string",
  "total_weeks": number,
  "weekly_hours": number,
  "weeks": [
    {
      "weekNumber": number,
      "title": "string",
      "learningObjectives": ["string"],
      "skillsCovered": ["string"],
      "estimatedHours": number,
      "actionItems": ["string"],
      "resources": [
        {
          "title": "string",
          "type": "free_course|interactive_notebook|official_docs|open_courseware|domain_article|platform_redirect",
          "url": "string",
          "platform": "string"
        }
      ],
      "mini_project": {
        "title": "string",
        "description": "string",
        "requirements": ["string"]
      }
    }
  ],
  "capstone_projects": [
    {
      "title": "string",
      "description": "string",
      "expected_output": "string",
      "requirements": ["string"],
      "skills_tested": ["string"]
    }
  ]
}

RULES:
1. "weeks" must be a flat array. NO "phases" or "modules".
2. "skillsCovered" must be specific technical skills.
3. Resources must NOT include YouTube. Use: Kaggle, fast.ai, HuggingFace, freeCodeCamp, MIT OCW, Stanford, Coursera (audit), edX (audit), Khan Academy, official docs, Towards Data Science, HBR.
4. Include mini_project for every 2-3 weeks.
5. Include 2-3 capstone_projects at the end.
6. Output VALID JSON only. No markdown, no comments.
7. If user is from a non-tech field, bridge from their domain to the tech skills needed.
"""


def generate_roadmap(
    target_field: str,
    learning_goal: str,
    current_skills: list,
    skill_levels: dict,
    jd_skills: list = None,
    weekly_hours: int = 10,
    duration_weeks: int = 12,
) -> dict:
    """Generate a personalized learning roadmap via LLM."""

    skills_str = ", ".join(current_skills) if current_skills else "None"
    levels_str = ", ".join([f"{k}: {v}" for k, v in skill_levels.items()]) if skill_levels else "No prior skills"
    jd_str = ", ".join(jd_skills) if jd_skills else "No specific job description"

    user_prompt = f"""
Generate a highly personalized learning roadmap for this student:

Target Field: {target_field}
Learning Goal: {learning_goal}
Current Skills: {skills_str}
Skill Levels: {levels_str}
Job Description Skills Required: {jd_str}
Weekly Available Hours: {weekly_hours}
Total Duration: {duration_weeks} weeks

Constraints:
- Tailor the curriculum to bridge their skill gap.
- Skip topics they already know well.
- Each week must have clear deliverables.
- Keep difficulty progressive.
- Resources must be FREE (no YouTube) — use Kaggle, fast.ai, MIT OCW, freeCodeCamp, official docs, etc.
- If the student is from a non-tech field (healthcare, law, business, design), bridge from their domain expertise to the tech skills they need.

Return ONLY valid JSON following the predefined schema.
"""

    try:
        roadmap = generate_json(ROADMAP_SYSTEM_PROMPT, user_prompt)
        roadmap = _ensure_roadmap_structure(roadmap, target_field, learning_goal)
        return roadmap
    except Exception as e:
        logger.error(f"Roadmap generation failed: {e}")
        # Return a fallback roadmap
        return _generate_fallback_roadmap(target_field, weekly_hours, duration_weeks)


def _ensure_roadmap_structure(roadmap: dict, field: str, goal: str) -> dict:
    """Post-process the LLM roadmap to guarantee required structure."""
    if not roadmap or "weeks" not in roadmap:
        return roadmap

    weeks = roadmap.get("weeks", [])

    # Ensure mini_project every 3 weeks if missing
    for i, week in enumerate(weeks):
        if "mini_project" not in week:
            week["mini_project"] = None
        # Add mini project every 3rd week if LLM forgot
        if (i + 1) % 3 == 0 and not week.get("mini_project"):
            title = week.get("title", f"Week {i+1} topic")
            skills = week.get("skillsCovered", [title])
            week["mini_project"] = {
                "title": f"Mini Project: Apply {title}",
                "description": f"Build a small project demonstrating your understanding of {', '.join(skills[:2])}",
                "requirements": skills[:3],
            }

    # Ensure capstone_projects exist (exactly 2)
    if not roadmap.get("capstone_projects") or len(roadmap.get("capstone_projects", [])) < 2:
        # Collect all skills from the roadmap
        all_skills = []
        for week in weeks:
            all_skills.extend(week.get("skillsCovered", []))
        unique_skills = list(dict.fromkeys(all_skills))  # preserve order, dedupe

        roadmap["capstone_projects"] = [
            {
                "title": f"Capstone 1: {field.title()} Full-Stack Application",
                "description": f"Build a comprehensive application combining all skills learned throughout the roadmap to achieve your goal: {goal}",
                "expected_output": "Fully functional application with documentation, deployed and accessible via GitHub",
                "requirements": unique_skills[:5] + ["Documentation", "Testing", "Deployment"],
                "skills_tested": unique_skills[:6],
            },
            {
                "title": f"Capstone 2: {field.title()} Portfolio & Presentation",
                "description": f"Create a professional portfolio showcasing all your projects, write-ups, and learnings. Present your journey from beginner to job-ready {field} professional.",
                "expected_output": "Portfolio website or PDF with project demos, code samples, and reflections",
                "requirements": ["Portfolio creation", "Project documentation", "Technical writing", "Self-reflection"],
                "skills_tested": unique_skills[:8],
            },
        ]

    return roadmap


def _generate_fallback_roadmap(field: str, weekly_hours: int, weeks: int) -> dict:
    """Generate a basic fallback roadmap when LLM is unavailable."""
    from environment.curriculum import get_topics_for_field

    topics = get_topics_for_field(field)
    roadmap_weeks = []

    for i, topic in enumerate(topics[:weeks]):
        week = {
            "weekNumber": i + 1,
            "title": topic.name,
            "learningObjectives": [f"Master {topic.name}"],
            "skillsCovered": [topic.id],
            "estimatedHours": min(topic.estimated_hours, weekly_hours),
            "actionItems": [f"Study {topic.name}", "Complete practice exercises"],
            "resources": [{"title": r.title, "type": r.type.value, "url": r.url, "platform": r.platform} for r in topic.resources[:3]],
            "mini_project": None
        }
        if (i + 1) % 3 == 0:
            week["mini_project"] = {
                "title": f"Mini Project: Apply {topic.name}",
                "description": f"Build a small project applying {topic.name} concepts",
                "requirements": [topic.name]
            }
        roadmap_weeks.append(week)

    return {
        "domain": field,
        "target_role": f"{field.title()} Professional",
        "total_weeks": len(roadmap_weeks),
        "weekly_hours": weekly_hours,
        "weeks": roadmap_weeks,
        "capstone_projects": [
            {
                "title": f"Capstone: {field.title()} Portfolio Project",
                "description": f"Build a comprehensive project showcasing your {field} skills",
                "expected_output": "Complete project with documentation",
                "requirements": ["All learned skills"],
                "skills_tested": [t.id for t in topics[:5]]
            }
        ]
    }
