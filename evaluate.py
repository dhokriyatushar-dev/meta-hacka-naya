"""
EduPath AI — Agent Comparison Evaluation (Upgrade 3)
Compare 3 agents on all 3 tasks:
1. Rule-based agent (deterministic fallback)
2. Enhanced ReAct agent (scratchpad-enhanced rule-based, LLM proxy)
3. PPO trained agent (neural network)

Produces evaluation_results.json, episode_rewards.csv, and learning_curve.json.
"""
import os
import sys
import json
import csv
import time
import argparse
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from environment.env import EduPathEnv
from environment.models import Action, ActionType, QuizDifficulty
from environment.student import student_manager
from environment.curriculum import TOPIC_GRAPH, get_available_topics
from environment.graders import grade_task1, grade_task2, grade_task3


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

GRADERS = {
    "task1_easy": grade_task1,
    "task2_medium": grade_task2,
    "task3_hard": grade_task3,
}


# ═══════════════════════════════════════════════════════════
#  Rule-Based Agent (basic, no memory)
# ═══════════════════════════════════════════════════════════

def _rule_based_decision(observation: dict) -> dict:
    """Deterministic rule-based agent (baseline, no scratchpad)."""
    available = observation.get("available_topics", [])
    completed = observation.get("completed_topics", [])
    current = observation.get("current_topic")
    quiz_history = observation.get("quiz_history_summary", {})
    projects_done = observation.get("completed_projects", [])
    topics_since_project = len(completed) - len(projects_done) * 3

    if current and current not in quiz_history:
        return {"type": "assign_quiz", "topic_id": current}
    if topics_since_project >= 3 and current:
        return {"type": "assign_mini_project", "topic_id": current}
    if current and quiz_history.get(current, 0) >= 70 and available:
        return {"type": "recommend_topic", "topic_id": available[0]}
    if current and current in quiz_history and quiz_history.get(current, 0) < 70:
        return {"type": "assign_quiz", "topic_id": current}
    if available:
        return {"type": "recommend_topic", "topic_id": available[0]}
    if observation.get("job_readiness_score", 0) >= 0.8:
        return {"type": "mark_job_ready"}
    if not available and len(completed) > 0:
        return {"type": "assign_capstone", "topic_id": completed[-1] if completed else "python_basics"}
    return {"type": "recommend_resource", "topic_id": current or "python_basics"}


# ═══════════════════════════════════════════════════════════
#  Enhanced ReAct Agent (scratchpad-enhanced, no LLM needed)
# ═══════════════════════════════════════════════════════════

class EvalReActAgent:
    """
    Enhanced rule-based agent with scratchpad memory.
    Matches the ReAct fallback logic from inference.py.
    This is the evaluation proxy for the LLM ReAct agent.
    """

    def __init__(self):
        self.topic_attempts = {}   # topic_id -> [scores]
        self.topics_recommended = []
        self.topics_completed = []
        self.projects_assigned = 0
        self.topics_since_project = 0

    def decide(self, observation: dict) -> dict:
        """Enhanced decision with scratchpad intelligence."""
        available = observation.get("available_topics", [])
        completed = observation.get("completed_topics", [])
        current = observation.get("current_topic")
        quiz_history = observation.get("quiz_history_summary", {})
        projects_done = observation.get("completed_projects", [])
        job_readiness = observation.get("job_readiness_score", 0)
        total_steps = observation.get("total_steps", 0)
        topics_since_project = len(completed) - len(projects_done) * 3

        # 1. If current topic has failed twice with <50% → assign resource first
        if current and current in quiz_history:
            scores = self.topic_attempts.get(current, [])
            low_scores = [s for s in scores if s < 50]
            if len(low_scores) >= 2 and total_steps < 60:
                return {"type": "recommend_resource", "topic_id": current}

        # 2. If current topic not yet quizzed → assign quiz
        if current and current not in quiz_history:
            return {"type": "assign_quiz", "topic_id": current}

        # 3. Every 3 completed topics → assign mini project
        if topics_since_project >= 3 and current:
            self.projects_assigned += 1
            self.topics_since_project = 0
            return {"type": "assign_mini_project", "topic_id": current}

        # 4. If current topic quizzed and passed → recommend next topic
        if current and quiz_history.get(current, 0) >= 70:
            if available:
                # Prefer topics with lower difficulty first (bridge strategy)
                best = available[0]
                best_score = -1
                for tid in available:
                    topic = TOPIC_GRAPH.get(tid)
                    if topic:
                        prereq_met = sum(1 for p in topic.prerequisites if p in completed)
                        score = prereq_met * 2 + (5 - topic.difficulty)
                        if score > best_score:
                            best_score = score
                            best = tid
                self.topics_since_project += 1
                return {"type": "recommend_topic", "topic_id": best}

        # 5. If current topic failed → retry quiz (scratchpad tracks)
        if current and current in quiz_history and quiz_history.get(current, 0) < 70:
            return {"type": "assign_quiz", "topic_id": current}

        # 6. If no current topic → recommend best available
        if available:
            best = available[0]
            best_score = -1
            for tid in available:
                topic = TOPIC_GRAPH.get(tid)
                if topic:
                    prereq_met = sum(1 for p in topic.prerequisites if p in completed)
                    score = prereq_met * 2 + (5 - topic.difficulty)
                    if score > best_score:
                        best_score = score
                        best = tid
            return {"type": "recommend_topic", "topic_id": best}

        # 7. If job readiness high → mark ready
        if job_readiness >= 0.8:
            return {"type": "mark_job_ready"}

        # 8. No available topics → assign capstone
        if not available and len(completed) > 0:
            return {"type": "assign_capstone", "topic_id": completed[-1]}

        return {"type": "recommend_resource", "topic_id": current or "python_basics"}

    def record(self, action: dict, observation: dict):
        """Record step result for scratchpad tracking."""
        action_type = action.get("type", "")
        topic_id = action.get("topic_id")
        quiz_history = observation.get("quiz_history_summary", {})

        if action_type == "assign_quiz" and topic_id:
            score = quiz_history.get(topic_id, 0)
            if topic_id not in self.topic_attempts:
                self.topic_attempts[topic_id] = []
            self.topic_attempts[topic_id].append(score)


# ═══════════════════════════════════════════════════════════
#  Episode Runners
# ═══════════════════════════════════════════════════════════

def _create_env_and_student(task_id: str, seed: int):
    """Create an environment and student for a task."""
    profile = TASK_PROFILES[task_id]
    env = EduPathEnv(seed=seed)
    student = student_manager.create(name=profile.get("name", "Eval Agent"))
    student_manager.update_from_onboarding(student.id, profile)
    obs = env.reset(student_id=student.id, seed=seed)
    return env, student, obs.model_dump()


def run_rule_based(task_id: str, seed: int = 42, max_steps: int = None) -> tuple:
    """Run rule-based agent on a task. Returns (score, total_reward, steps)."""
    max_steps = max_steps or TASK_MAX_STEPS[task_id]
    env, student, observation = _create_env_and_student(task_id, seed)

    total_reward = 0.0
    steps = 0

    for step in range(max_steps):
        action_dict = _rule_based_decision(observation)
        action_type = ActionType(action_dict["type"])
        action = Action(
            type=action_type,
            topic_id=action_dict.get("topic_id"),
            project_id=action_dict.get("project_id"),
        )
        result = env.step(action)
        total_reward += result.reward.value
        observation = result.observation.model_dump()
        steps = step + 1
        if result.done:
            break

    student = student_manager.get(student.id)
    score = GRADERS[task_id](student)
    return score, total_reward, steps


def run_react(task_id: str, seed: int = 42, max_steps: int = None) -> tuple:
    """Run enhanced ReAct agent on a task. Returns (score, total_reward, steps)."""
    max_steps = max_steps or TASK_MAX_STEPS[task_id]
    env, student, observation = _create_env_and_student(task_id, seed)

    agent = EvalReActAgent()
    total_reward = 0.0
    steps = 0

    for step in range(max_steps):
        action_dict = agent.decide(observation)
        action_type = ActionType(action_dict["type"])
        action = Action(
            type=action_type,
            topic_id=action_dict.get("topic_id"),
            project_id=action_dict.get("project_id"),
        )
        result = env.step(action)
        total_reward += result.reward.value
        observation = result.observation.model_dump()

        # Record in scratchpad
        agent.record(action_dict, observation)

        steps = step + 1
        if result.done:
            break

    student = student_manager.get(student.id)
    score = GRADERS[task_id](student)
    return score, total_reward, steps


def run_ppo(task_id: str, model_path: str = None, seed: int = 42, max_steps: int = None) -> tuple:
    """Run PPO trained agent on a task. Returns (score, total_reward, steps)."""
    try:
        from stable_baselines3 import PPO as PPOModel
        from gym_wrapper import EduPathGymEnv
    except ImportError:
        print("  ⚠ stable-baselines3 not installed, skipping PPO evaluation")
        return 0.0, 0.0, 0

    max_steps = max_steps or TASK_MAX_STEPS[task_id]

    if model_path is None:
        model_path = os.path.join("models", f"ppo_edupath_{task_id}")

    if not os.path.exists(model_path + ".zip"):
        print(f"  ⚠ PPO model not found at {model_path}.zip, skipping")
        return 0.0, 0.0, 0

    model = PPOModel.load(model_path)
    env = EduPathGymEnv(task_id=task_id, seed=seed)
    obs, _ = env.reset(seed=seed)

    total_reward = 0.0
    steps = 0
    done = False

    while not done and steps < max_steps:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(int(action))
        total_reward += reward
        done = terminated or truncated
        steps += 1

    # Grade using the student created by gym wrapper
    student = student_manager.get(env._student_id)
    score = GRADERS[task_id](student) if student else 0.0
    return score, total_reward, steps


# ═══════════════════════════════════════════════════════════
#  Main Evaluation
# ═══════════════════════════════════════════════════════════

def evaluate_all(num_episodes: int = 10, results_dir: str = "results"):
    """Evaluate all agents on all tasks."""
    os.makedirs(results_dir, exist_ok=True)

    agents = ["rule_based", "react_enhanced", "ppo_trained"]
    agent_runners = {
        "rule_based": run_rule_based,
        "react_enhanced": run_react,
        "ppo_trained": run_ppo,
    }
    agent_display = {
        "rule_based": "Rule-based",
        "react_enhanced": "LLM ReAct",
        "ppo_trained": "PPO Trained",
    }
    tasks = ["task1_easy", "task2_medium", "task3_hard"]

    results = {}
    reward_results = {}
    episode_data = []

    for agent_type in agents:
        results[agent_type] = {}
        reward_results[agent_type] = {}
        runner = agent_runners[agent_type]

        for task_id in tasks:
            scores = []
            rewards = []
            all_steps = []

            print(f"  Running {agent_display[agent_type]:18s} on {task_id}...", end=" ", flush=True)
            for ep in range(num_episodes):
                seed = 42 + ep
                score, reward, steps = runner(task_id, seed=seed)
                scores.append(score)
                rewards.append(reward)
                all_steps.append(steps)
                episode_data.append({
                    "episode": ep + 1,
                    "reward": round(reward, 4),
                    "score": round(score, 4),
                    "task": task_id,
                    "agent_type": agent_type,
                    "steps": steps,
                })

            mean_score = float(np.mean(scores)) if scores else 0.0
            mean_reward = float(np.mean(rewards)) if rewards else 0.0
            results[agent_type][task_id] = round(mean_score, 4)
            reward_results[agent_type][task_id] = round(mean_reward, 4)
            print(f"score={mean_score:.4f}  reward={mean_reward:.2f}")

    # Print comparison table
    print(f"\n{'='*70}")
    print(f"  AGENT COMPARISON — MEAN SCORES OVER {num_episodes} EPISODES")
    print(f"{'='*70}")
    print(f"  {'Agent':<18} | {'Task1':>7} | {'Task2':>7} | {'Task3':>7} | {'Avg':>7}")
    print(f"  {'-'*18}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}")

    for agent_type in agents:
        name = agent_display[agent_type]
        t1 = results[agent_type].get("task1_easy", 0.0)
        t2 = results[agent_type].get("task2_medium", 0.0)
        t3 = results[agent_type].get("task3_hard", 0.0)
        avg = (t1 + t2 + t3) / 3
        print(f"  {name:<18} | {t1:>7.4f} | {t2:>7.4f} | {t3:>7.4f} | {avg:>7.4f}")

    print(f"{'='*70}")

    # Reward comparison
    print(f"\n  {'Agent':<18} | {'Task1':>7} | {'Task2':>7} | {'Task3':>7} | {'Avg':>7}")
    print(f"  {'-'*18}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}")
    for agent_type in agents:
        name = agent_display[agent_type]
        r1 = reward_results[agent_type].get("task1_easy", 0.0)
        r2 = reward_results[agent_type].get("task2_medium", 0.0)
        r3 = reward_results[agent_type].get("task3_hard", 0.0)
        avg = (r1 + r2 + r3) / 3
        print(f"  {name:<18} | {r1:>7.2f} | {r2:>7.2f} | {r3:>7.2f} | {avg:>7.2f}")
    print(f"{'='*70}\n")

    # Save results
    full_results = {
        "scores": results,
        "rewards": reward_results,
        "num_episodes": num_episodes,
    }
    results_path = os.path.join(results_dir, "evaluation_results.json")
    with open(results_path, "w") as f:
        json.dump(full_results, f, indent=2)
    print(f"Results saved to {results_path}")

    # Save episode data as CSV
    csv_path = os.path.join(results_dir, "episode_rewards.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "reward", "score", "task", "agent_type", "steps"])
        writer.writeheader()
        writer.writerows(episode_data)
    print(f"Episode data saved to {csv_path}")

    # Generate learning curve JSON (from training data if available)
    _generate_learning_curve(results_dir)

    return results


def _generate_learning_curve(results_dir: str):
    """Combine per-task learning curves into a single JSON."""
    combined = {}
    for task_id in ["task1_easy", "task2_medium", "task3_hard"]:
        curve_path = os.path.join(results_dir, f"learning_curve_{task_id}.json")
        if os.path.exists(curve_path):
            with open(curve_path, "r") as f:
                combined[task_id] = json.load(f)

    if combined:
        combined_path = os.path.join(results_dir, "learning_curve.json")
        with open(combined_path, "w") as f:
            json.dump(combined, f, indent=2)
        print(f"Combined learning curve saved to {combined_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate EduPath AI Agents")
    parser.add_argument("--episodes", type=int, default=10,
                        help="Number of evaluation episodes per task")
    parser.add_argument("--results-dir", type=str, default="results",
                        help="Directory to save results")
    args = parser.parse_args()

    evaluate_all(num_episodes=args.episodes, results_dir=args.results_dir)
