"""
EduPath AI — Gymnasium Wrapper (Upgrade 3)
Wraps EduPathEnv in OpenAI Gym interface for PPO training.
Works WITHOUT needing an LLM API key — the PPO policy is a neural network.
"""
import os
import sys
import numpy as np
import gymnasium
from gymnasium import spaces

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from environment.env import EduPathEnv
from environment.models import Action, ActionType, QuizDifficulty
from environment.student import student_manager
from environment.curriculum import TOPIC_GRAPH, get_available_topics


# Map integer indices to ActionType enum values
ACTION_TYPE_MAP = {
    0: ActionType.RECOMMEND_TOPIC,
    1: ActionType.ASSIGN_QUIZ,
    2: ActionType.ASSIGN_MINI_PROJECT,
    3: ActionType.ASSIGN_CAPSTONE,
    4: ActionType.RECOMMEND_RESOURCE,
    5: ActionType.SUGGEST_EVENT,
    6: ActionType.MARK_JOB_READY,
}

# Task profiles for training
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


class EduPathGymEnv(gymnasium.Env):
    """
    Gymnasium-compatible wrapper for EduPath AI environment.
    Converts the Pydantic-based environment into numpy arrays for RL training.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, task_id: str = "task2_medium", seed: int = 42):
        super().__init__()
        self.task_id = task_id
        self.seed_val = seed

        # Action space: 7 discrete action types
        self.action_space = spaces.Discrete(7)

        # Observation space: flattened student state as float32 array
        # Fields encoded (all normalized 0-1):
        # [0] completed_topics_count (/ 32)
        # [1] available_topics_count (/ 32)
        # [2] job_readiness_score (already 0-1)
        # [3] avg_quiz_score (/ 100)
        # [4] completed_projects_count (/ 12)
        # [5] current_skill_avg (already 0-1)
        # [6] badges_earned (/ 30)
        # [7] total_steps (/ 100)
        # [8] weekly_hours (/ 20)
        # [9] has_current_topic (0 or 1)
        # [10] num_quiz_attempts (/ 50)
        # [11] quiz_pass_rate (0-1)
        # [12] steps_remaining_ratio (0-1)
        # [13] topics_since_last_project (/ 10)
        # [14] current_topic_skill (0-1)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(15,), dtype=np.float32
        )

        self.env = None
        self._student_id = None
        self._observation = None
        self._all_topic_ids = sorted(TOPIC_GRAPH.keys())

    def reset(self, seed=None, options=None):
        """Reset the environment and return initial observation."""
        if seed is not None:
            self.seed_val = seed

        self.env = EduPathEnv(seed=self.seed_val)
        profile = TASK_PROFILES[self.task_id]

        # Create student
        student = student_manager.create(name=profile.get("name", "PPO Agent"))
        student_manager.update_from_onboarding(student.id, profile)
        self._student_id = student.id

        obs_pydantic = self.env.reset(student_id=self._student_id, seed=self.seed_val)
        self._observation = obs_pydantic.model_dump()

        return self._encode_observation(self._observation), {}

    def step(self, action_int: int):
        """Execute action and return (obs, reward, terminated, truncated, info)."""
        action = self._decode_action(action_int)
        result = self.env.step(action)

        self._observation = result.observation.model_dump()
        reward = result.reward.value
        terminated = result.done and result.reward.is_terminal
        truncated = result.done and not result.reward.is_terminal

        info = result.info
        info["reward_reason"] = result.reward.reason

        obs_array = self._encode_observation(self._observation)
        return obs_array, reward, terminated, truncated, info

    def _encode_observation(self, obs: dict) -> np.ndarray:
        """Flatten StudentObservation to numpy float32 array."""
        completed = obs.get("completed_topics", [])
        available = obs.get("available_topics", [])
        quiz_history = obs.get("quiz_history_summary", {})
        skill_levels = obs.get("skill_levels", {})
        projects = obs.get("completed_projects", [])
        total_steps = obs.get("total_steps", 0)

        # Compute derived features
        avg_quiz = (sum(quiz_history.values()) / max(len(quiz_history), 1)) if quiz_history else 0.0
        avg_skill = (sum(skill_levels.values()) / max(len(skill_levels), 1)) if skill_levels else 0.0
        num_quizzes = len(quiz_history)
        quiz_pass_rate = (sum(1 for s in quiz_history.values() if s >= 70) / max(num_quizzes, 1)) if num_quizzes > 0 else 0.0
        topics_since_project = len(completed) - len(projects) * 3

        current_topic = obs.get("current_topic")
        current_skill = skill_levels.get(current_topic, 0.0) if current_topic else 0.0

        features = np.array([
            len(completed) / 32.0,                          # [0]
            len(available) / 32.0,                          # [1]
            obs.get("job_readiness_score", 0.0),            # [2]
            avg_quiz / 100.0,                               # [3]
            len(projects) / 12.0,                           # [4]
            avg_skill,                                      # [5]
            obs.get("badges_earned", 0) / 30.0,             # [6]
            total_steps / 100.0,                            # [7]
            obs.get("weekly_hours", 10) / 20.0,             # [8]
            1.0 if current_topic else 0.0,                  # [9]
            num_quizzes / 50.0,                             # [10]
            quiz_pass_rate,                                 # [11]
            max(0, (100 - total_steps)) / 100.0,            # [12]
            max(0, min(topics_since_project, 10)) / 10.0,   # [13]
            current_skill,                                  # [14]
        ], dtype=np.float32)

        return np.clip(features, 0.0, 1.0)

    def _decode_action(self, action_int: int) -> Action:
        """Convert integer action to Action object with heuristic topic/project selection."""
        action_type = ACTION_TYPE_MAP.get(action_int, ActionType.RECOMMEND_TOPIC)
        topic_id = None
        project_id = None

        obs = self._observation or {}
        available = obs.get("available_topics", [])
        completed = obs.get("completed_topics", [])
        current = obs.get("current_topic")
        quiz_history = obs.get("quiz_history_summary", {})

        if action_type == ActionType.RECOMMEND_TOPIC:
            # Pick best available topic based on prerequisites
            if available:
                # Prefer topics with more completed prereqs
                best_topic = available[0]
                best_score = -1
                for tid in available:
                    topic = TOPIC_GRAPH.get(tid)
                    if topic:
                        prereq_complete = sum(1 for p in topic.prerequisites if p in completed)
                        score = prereq_complete + (1 if topic.difficulty <= 2 else 0)
                        if score > best_score:
                            best_score = score
                            best_topic = tid
                topic_id = best_topic

        elif action_type == ActionType.ASSIGN_QUIZ:
            # Quiz the current topic, or last recommended
            topic_id = current
            if not topic_id and completed:
                # Quiz a completed topic that hasn't been quizzed
                for t in reversed(completed):
                    if t not in quiz_history:
                        topic_id = t
                        break
            if not topic_id and available:
                topic_id = available[0]

        elif action_type in (ActionType.ASSIGN_MINI_PROJECT, ActionType.ASSIGN_CAPSTONE):
            topic_id = current or (completed[-1] if completed else None)

        elif action_type == ActionType.RECOMMEND_RESOURCE:
            topic_id = current or (available[0] if available else None)

        return Action(
            type=action_type,
            topic_id=topic_id,
            project_id=project_id,
        )

    def render(self, mode="human"):
        """Optional render for debugging."""
        if self._observation:
            print(f"Step {self._observation.get('total_steps', '?')}: "
                  f"Completed={len(self._observation.get('completed_topics', []))} "
                  f"Available={len(self._observation.get('available_topics', []))} "
                  f"JR={self._observation.get('job_readiness_score', 0):.2f}")


def make_env(task_id: str = "task2_medium", seed: int = 42):
    """Factory function to create the environment."""
    def _init():
        return EduPathGymEnv(task_id=task_id, seed=seed)
    return _init


if __name__ == "__main__":
    # Quick test
    env = EduPathGymEnv(task_id="task1_easy")
    obs, info = env.reset()
    print(f"Observation shape: {obs.shape}")
    print(f"Observation: {obs}")

    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Step {i+1}: action={action}, reward={reward:.2f}, "
              f"terminated={terminated}, truncated={truncated}")
        if terminated or truncated:
            break

    print("Gym wrapper test passed!")
