"""
EduPath AI — Baseline Inference Script
Uses OpenAI Client for all LLM calls (hackathon requirement).
OpenEnv-compliant: observes student state → decides action → environment responds.
"""
import os
import sys
import json
import logging
import random

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from environment.env import EduPathEnv
from environment.models import Action, ActionType
from environment.student import student_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Seed for reproducibility ──
SEED = 42
random.seed(SEED)


def _get_openai_client():
    """Get OpenAI-compatible client using required env vars."""
    from openai import OpenAI

    api_base_url = os.getenv("API_BASE_URL")
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    hf_token = os.getenv("HF_TOKEN", "")

    if not api_base_url:
        return None, model_name  # Fallback to rule-based

    client = OpenAI(
        base_url=api_base_url,
        api_key=hf_token or os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    )
    return client, model_name


def get_agent_decision(observation: dict) -> Action:
    """
    AI agent makes a tutoring decision based on student state.
    Uses OpenAI Client when available, falls back to rule-based logic.
    """
    client, model_name = _get_openai_client()

    if client and os.getenv("API_BASE_URL"):
        return _llm_decision(observation, client, model_name)
    else:
        return _rule_based_decision(observation)


def _llm_decision(observation: dict, client, model_name: str) -> Action:
    """Use OpenAI Client to decide next action."""
    system_prompt = """You are an AI tutoring agent. Based on the student's current state, decide the best action.

Return JSON with:
{
  "type": "recommend_topic|assign_quiz|assign_mini_project|assign_capstone|recommend_resource|mark_job_ready",
  "topic_id": "optional topic id",
  "project_id": "optional project id",
  "reasoning": "why this action"
}

Rules:
1. If student has available topics with met prerequisites → recommend_topic
2. If student just completed a topic → assign_quiz
3. After every 2-3 topics → assign_mini_project
4. When all quizzes passed and projects done → mark_job_ready
5. Respect prerequisites — never recommend a topic with unmet prereqs"""

    user_prompt = f"Student state:\n{json.dumps(observation, indent=2)}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
        action_type = result.get("type", "recommend_topic")
        return Action(
            type=ActionType(action_type),
            topic_id=result.get("topic_id"),
            project_id=result.get("project_id"),
        )
    except Exception as e:
        logger.warning(f"LLM decision failed: {e}, falling back to rules")
        return _rule_based_decision(observation)


def _rule_based_decision(observation: dict) -> Action:
    """Deterministic rule-based fallback agent for reproducible scores."""
    available = observation.get("available_topics", [])
    completed = observation.get("completed_topics", [])
    current = observation.get("current_topic")
    quiz_history = observation.get("quiz_history_summary", {})
    projects_done = observation.get("completed_projects", [])
    topics_since_project = len(completed) - len(projects_done) * 3

    # 1. If current topic not yet quizzed → assign quiz
    if current and current not in quiz_history:
        return Action(type=ActionType.ASSIGN_QUIZ, topic_id=current)

    # 2. Every 3 topics → assign mini project
    if topics_since_project >= 3 and current:
        return Action(type=ActionType.ASSIGN_MINI_PROJECT, topic_id=current)

    # 3. If current topic quizzed and passed → recommend next topic
    if current and quiz_history.get(current, 0) >= 70 and available:
        return Action(type=ActionType.RECOMMEND_TOPIC, topic_id=available[0])

    # 4. If current topic failed → retry the quiz (not just resource)
    #    The env boosts skill on RECOMMEND_RESOURCE, so retrying helps
    if current and current in quiz_history and quiz_history.get(current, 0) < 70:
        # Retry the quiz directly — skill was already boosted by recommend_topic
        return Action(type=ActionType.ASSIGN_QUIZ, topic_id=current)

    # 5. If no current topic → recommend first available
    if available:
        return Action(type=ActionType.RECOMMEND_TOPIC, topic_id=available[0])

    # 6. If job readiness high → mark ready
    if observation.get("job_readiness_score", 0) >= 0.8:
        return Action(type=ActionType.MARK_JOB_READY)

    # 7. If no available topics but not job ready → assign capstone
    if not available and len(completed) > 0:
        return Action(type=ActionType.ASSIGN_CAPSTONE, topic_id=completed[-1] if completed else "python_basics")

    # Default
    return Action(type=ActionType.RECOMMEND_RESOURCE, topic_id=current or "python_basics")


def run_episode(student_id: str = None, max_steps: int = 50):
    """Run a full tutoring episode and return results."""
    env = EduPathEnv()
    obs = env.reset(student_id)

    logger.info("=" * 60)
    logger.info("EduPath AI — Inference Run (OpenAI Client)")
    logger.info("=" * 60)
    logger.info(f"Student: {obs.student_id}")
    logger.info(f"Field: {obs.target_field}")
    logger.info(f"Available topics: {obs.available_topics}")
    logger.info(f"API_BASE_URL: {os.getenv('API_BASE_URL', 'NOT SET (rule-based mode)')}")
    logger.info(f"MODEL_NAME: {os.getenv('MODEL_NAME', 'N/A')}")

    total_reward = 0.0

    for step in range(max_steps):
        # Agent observes and decides
        obs_dict = obs.model_dump()
        action = get_agent_decision(obs_dict)

        # Environment steps
        result = env.step(action)

        total_reward += result.reward.value
        logger.info(f"\nStep {step + 1}: {action.type.value} → {action.topic_id or action.project_id or ''}")
        logger.info(f"  Reward: {result.reward.value:+.2f} ({result.reward.reason})")
        logger.info(f"  Total reward: {total_reward:+.2f}")

        obs = result.observation

        if result.done:
            logger.info(f"\n🏁 Episode finished! Total reward: {total_reward:+.2f}")
            break

    return {
        "student_id": obs.student_id,
        "total_steps": env.total_steps,
        "total_reward": round(total_reward, 4),
        "done": env.done,
        "final_state": env.state(),
    }


def run_task(task_num: int):
    """Run a specific task (1, 2, or 3) and return graded score."""
    from environment.graders import grade_task1, grade_task2, grade_task3

    profiles = {
        1: {
            "name": "Alex Beginner",
            "target_field": "tech",
            "learning_goal": "Learn Python programming from scratch",
            "weekly_hours": 10,
        },
        2: {
            "name": "Jordan Analyst",
            "target_field": "tech",
            "learning_goal": "Become a Data Analyst in 3 months",
            "weekly_hours": 15,
            "skills": [{"skill": "Python", "level": "Intermediate", "proficiency": 0.4}],
            "resume_skills": ["python", "excel"],
        },
        3: {
            "name": "Dr. Priya Shah",
            "target_field": "healthcare",
            "learning_goal": "Apply AI to medical imaging and clinical data analysis",
            "weekly_hours": 10,
            "skills": [
                {"skill": "Biology", "level": "Expert", "proficiency": 0.9},
                {"skill": "Statistics", "level": "Beginner", "proficiency": 0.3},
            ],
            "resume_skills": ["medicine", "clinical research", "biology"],
        },
    }

    max_steps_map = {1: 30, 2: 50, 3: 80}

    profile = profiles[task_num]
    student = student_manager.create(name=profile["name"])
    student_manager.update_from_onboarding(student.id, profile)

    result = run_episode(student.id, max_steps=max_steps_map[task_num])

    # Grade
    graders = {1: grade_task1, 2: grade_task2, 3: grade_task3}
    final = student_manager.get(student.id)
    score = graders[task_num](final)

    logger.info(f"\n{'='*60}")
    logger.info(f"Task {task_num} Score: {score:.4f}")
    logger.info(f"{'='*60}")

    return score


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EduPath AI Inference")
    parser.add_argument("--task", type=int, choices=[1, 2, 3], help="Run specific task (1, 2, or 3)")
    parser.add_argument("--all", action="store_true", help="Run all 3 tasks and print scores")
    args = parser.parse_args()

    if args.all:
        scores = {}
        for t in [1, 2, 3]:
            logger.info(f"\n{'#'*60}")
            logger.info(f"  RUNNING TASK {t}")
            logger.info(f"{'#'*60}")
            scores[f"task{t}"] = run_task(t)

        print("\n" + "=" * 40)
        print("  BASELINE SCORES")
        print("=" * 40)
        for k, v in scores.items():
            print(f"  {k}: {v:.4f}")
        print("=" * 40)

    elif args.task:
        score = run_task(args.task)
        print(f"Task {args.task} score: {score:.4f}")

    else:
        # Default: create test student and run episode
        student = student_manager.create(name="Test Student")
        student_manager.update_from_onboarding(student.id, {
            "target_field": "tech",
            "learning_goal": "Become an ML Engineer",
            "weekly_hours": 10,
        })
        result = run_episode(student.id)
        print(json.dumps(result, indent=2, default=str))
