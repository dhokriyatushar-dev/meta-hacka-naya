"""
EduPath AI — Baseline Inference Script
Uses OpenAI Client for all LLM calls (hackathon requirement).
Supports both HTTP mode (against running server) and direct mode (import env).
Emits structured [START], [STEP], [END] stdout logs per hackathon spec.
"""
import os
import sys
import json
import time
import random
import logging
import argparse
import requests
from datetime import datetime, timezone

# Add backend to path for direct mode
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Seed for reproducibility ──
SEED = 42
random.seed(SEED)

# ── Environment configuration ──
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN", "")


# ═══════════════════════════════════════════════════════════
#  Structured Logging — [START], [STEP], [END]
# ═══════════════════════════════════════════════════════════

def log_start(task_id: str, student_id: str, model: str):
    """Emit [START] structured log to stdout."""
    entry = {
        "task_id": task_id,
        "student_id": student_id,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_base_url": API_BASE_URL or "rule-based",
    }
    print(f"[START] {json.dumps(entry)}", flush=True)


def log_step(step: int, action: str, topic_id: str, reward: float, done: bool, info: dict = None):
    """Emit [STEP] structured log to stdout."""
    entry = {
        "step": step,
        "action": action,
        "topic_id": topic_id or "",
        "reward": round(reward, 4),
        "done": done,
    }
    if info:
        entry["info"] = info
    print(f"[STEP] {json.dumps(entry)}", flush=True)


def log_end(task_id: str, total_steps: int, total_reward: float, score: float):
    """Emit [END] structured log to stdout."""
    entry = {
        "task_id": task_id,
        "total_steps": total_steps,
        "total_reward": round(total_reward, 4),
        "score": round(score, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"[END] {json.dumps(entry)}", flush=True)


# ═══════════════════════════════════════════════════════════
#  OpenAI Client — LLM Decision Making
# ═══════════════════════════════════════════════════════════

def _get_openai_client():
    """Get OpenAI-compatible client using required env vars."""
    from openai import OpenAI

    if not API_BASE_URL:
        return None, MODEL_NAME  # Fallback to rule-based

    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN or os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    )
    return client, MODEL_NAME


def _llm_decision(observation: dict, client, model_name: str) -> dict:
    """Use OpenAI Client to decide next action."""
    system_prompt = """You are an AI tutoring agent. Based on the student's current state, decide the best action.

Return JSON with:
{
  "type": "recommend_topic|assign_quiz|assign_mini_project|assign_capstone|recommend_resource|mark_job_ready",
  "topic_id": "optional topic id",
  "project_id": "optional project id"
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
        return {
            "type": result.get("type", "recommend_topic"),
            "topic_id": result.get("topic_id"),
            "project_id": result.get("project_id"),
        }
    except Exception as e:
        logger.warning(f"LLM decision failed: {e}, falling back to rules")
        return None


def _rule_based_decision(observation: dict) -> dict:
    """Deterministic rule-based fallback agent for reproducible scores."""
    available = observation.get("available_topics", [])
    completed = observation.get("completed_topics", [])
    current = observation.get("current_topic")
    quiz_history = observation.get("quiz_history_summary", {})
    projects_done = observation.get("completed_projects", [])
    topics_since_project = len(completed) - len(projects_done) * 3

    # 1. If current topic not yet quizzed → assign quiz
    if current and current not in quiz_history:
        return {"type": "assign_quiz", "topic_id": current}

    # 2. Every 3 topics → assign mini project
    if topics_since_project >= 3 and current:
        return {"type": "assign_mini_project", "topic_id": current}

    # 3. If current topic quizzed and passed → recommend next topic
    if current and quiz_history.get(current, 0) >= 70 and available:
        return {"type": "recommend_topic", "topic_id": available[0]}

    # 4. If current topic failed → retry the quiz
    if current and current in quiz_history and quiz_history.get(current, 0) < 70:
        return {"type": "assign_quiz", "topic_id": current}

    # 5. If no current topic → recommend first available
    if available:
        return {"type": "recommend_topic", "topic_id": available[0]}

    # 6. If job readiness high → mark ready
    if observation.get("job_readiness_score", 0) >= 0.8:
        return {"type": "mark_job_ready"}

    # 7. No available topics → assign capstone
    if not available and len(completed) > 0:
        return {"type": "assign_capstone", "topic_id": completed[-1] if completed else "python_basics"}

    # Default
    return {"type": "recommend_resource", "topic_id": current or "python_basics"}


def get_agent_decision(observation: dict) -> dict:
    """AI agent makes a tutoring decision based on student state."""
    client, model_name = _get_openai_client()

    if client and API_BASE_URL:
        result = _llm_decision(observation, client, model_name)
        if result:
            return result

    return _rule_based_decision(observation)


# ═══════════════════════════════════════════════════════════
#  HTTP Client — Talks to the running server
# ═══════════════════════════════════════════════════════════

class EnvHTTPClient:
    """HTTP client for interacting with the OpenEnv server."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def reset(self, student_profile: dict = None, seed: int = 42) -> dict:
        """POST /reset → returns observation."""
        payload = {"seed": seed}
        if student_profile:
            payload["student_profile"] = student_profile
        resp = requests.post(f"{self.base_url}/reset", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def step(self, action: dict) -> dict:
        """POST /step → returns observation, reward, done, info."""
        resp = requests.post(f"{self.base_url}/step", json=action, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        """POST /state → returns current state."""
        resp = requests.post(f"{self.base_url}/state", json={}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def grade(self, task_id: str) -> float:
        """POST /grade → returns score for the task."""
        resp = requests.post(
            f"{self.base_url}/grade",
            json={"task_id": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("score", 0.0)


# ═══════════════════════════════════════════════════════════
#  Direct Mode — Import env class directly (fallback)
# ═══════════════════════════════════════════════════════════

class EnvDirectClient:
    """Direct client that imports the environment class."""

    def __init__(self):
        from environment.env import EduPathEnv
        from environment.models import Action, ActionType
        from environment.student import student_manager
        self.EduPathEnv = EduPathEnv
        self.Action = Action
        self.ActionType = ActionType
        self.student_manager = student_manager
        self.env = None
        self._current_student_id = None

    def reset(self, student_profile: dict = None, seed: int = 42) -> dict:
        random.seed(seed)
        self.env = self.EduPathEnv()

        if student_profile:
            student = self.student_manager.create(name=student_profile.get("name", "Agent"))
            self.student_manager.update_from_onboarding(student.id, student_profile)
            student_id = student.id
        else:
            student = self.student_manager.create(name="Test Agent")
            self.student_manager.update_from_onboarding(student.id, {
                "target_field": "tech",
                "learning_goal": "Learn Python",
                "weekly_hours": 10,
            })
            student_id = student.id

        self._current_student_id = student_id
        obs = self.env.reset(student_id)
        return {
            "observation": obs.model_dump(),
            "info": {"student_id": student_id},
        }

    def step(self, action_dict: dict) -> dict:
        from environment.models import QuizDifficulty
        action_type = self.ActionType(action_dict["type"])
        difficulty = None
        if action_dict.get("difficulty"):
            try:
                difficulty = QuizDifficulty(action_dict["difficulty"])
            except ValueError:
                pass
        action = self.Action(
            type=action_type,
            topic_id=action_dict.get("topic_id"),
            project_id=action_dict.get("project_id"),
            difficulty=difficulty,
        )
        result = self.env.step(action)
        return {
            "observation": result.observation.model_dump(),
            "reward": result.reward.model_dump(),
            "done": result.done,
            "info": result.info,
        }

    def state(self) -> dict:
        return self.env.state() if self.env else {}

    def grade(self, task_id: str) -> float:
        """Grade using direct grader import."""
        from environment.graders import grade_task1, grade_task2, grade_task3
        student = self.student_manager.get(self._current_student_id)
        if not student:
            return 0.0
        graders = {
            "task1_easy": grade_task1,
            "task2_medium": grade_task2,
            "task3_hard": grade_task3,
        }
        grader = graders.get(task_id)
        return grader(student) if grader else 0.0


def get_client(use_http: bool = True) -> object:
    """Get the appropriate client (HTTP or direct)."""
    if use_http:
        try:
            # Try to connect to running server
            resp = requests.get(f"{SERVER_URL}/health", timeout=5)
            if resp.status_code == 200:
                logger.info(f"Connected to server at {SERVER_URL}")
                return EnvHTTPClient(SERVER_URL)
        except Exception:
            logger.info("Server not running, falling back to direct mode")

    logger.info("Using direct environment mode")
    return EnvDirectClient()


# ═══════════════════════════════════════════════════════════
#  Episode Runner
# ═══════════════════════════════════════════════════════════

TASK_PROFILES = {
    "task1_easy": {
        "name": "Alex Beginner",
        "target_field": "tech",
        "learning_goal": "Learn Python programming from scratch",
        "weekly_hours": 10,
    },
    "task2_medium": {
        "name": "Jordan Analyst",
        "target_field": "tech",
        "learning_goal": "Become a Data Analyst in 3 months",
        "weekly_hours": 15,
        "skills": [{"skill": "Python", "level": "Intermediate", "proficiency": 0.4}],
        "resume_skills": ["python", "excel"],
    },
    "task3_hard": {
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

TASK_MAX_STEPS = {
    "task1_easy": 30,
    "task2_medium": 50,
    "task3_hard": 80,
}


def run_task(task_id: str, client) -> float:
    """Run a task episode and return graded score."""
    profile = TASK_PROFILES[task_id]
    max_steps = TASK_MAX_STEPS[task_id]

    # Reset environment
    reset_result = client.reset(student_profile=profile, seed=SEED)
    observation = reset_result["observation"]
    student_id = reset_result.get("info", {}).get("student_id", "unknown")

    # Emit [START]
    log_start(task_id, student_id, MODEL_NAME)

    total_reward = 0.0
    step_count = 0

    for step in range(max_steps):
        # Agent decides action
        action = get_agent_decision(observation)
        step_count = step + 1

        # Execute action via environment
        result = client.step(action)

        reward_val = result.get("reward", {}).get("value", 0.0)
        done = result.get("done", False)
        info = result.get("info", {})
        total_reward += reward_val

        # Emit [STEP]
        log_step(
            step=step_count,
            action=action.get("type", "unknown"),
            topic_id=action.get("topic_id", ""),
            reward=reward_val,
            done=done,
            info=info,
        )

        observation = result.get("observation", observation)

        if done:
            break

    # Grade the task via /grade endpoint (works both HTTP and direct)
    score = client.grade(task_id)

    # Emit [END]
    log_end(task_id, step_count, total_reward, score)

    return score


# ═══════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduPath AI Inference")
    parser.add_argument("--task", type=str, choices=["task1_easy", "task2_medium", "task3_hard"],
                        help="Run specific task")
    parser.add_argument("--all", action="store_true", help="Run all 3 tasks and print scores")
    parser.add_argument("--direct", action="store_true",
                        help="Use direct env import instead of HTTP client")
    args = parser.parse_args()

    client = get_client(use_http=not args.direct)

    if args.all:
        scores = {}
        for task_id in ["task1_easy", "task2_medium", "task3_hard"]:
            logger.info(f"\n{'#' * 60}")
            logger.info(f"  RUNNING {task_id.upper()}")
            logger.info(f"{'#' * 60}")
            scores[task_id] = run_task(task_id, client)

        print("\n" + "=" * 40)
        print("  BASELINE SCORES")
        print("=" * 40)
        for k, v in scores.items():
            print(f"  {k}: {v:.4f}")
        print("=" * 40)

    elif args.task:
        score = run_task(args.task, client)
        print(f"\n{args.task} score: {score:.4f}")

    else:
        # Default: run all tasks
        scores = {}
        for task_id in ["task1_easy", "task2_medium", "task3_hard"]:
            scores[task_id] = run_task(task_id, client)

        print("\n" + "=" * 40)
        print("  BASELINE SCORES")
        print("=" * 40)
        for k, v in scores.items():
            print(f"  {k}: {v:.4f}")
        print("=" * 40)
