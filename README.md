---
title: EduPath AI
emoji: 🎓
colorFrom: gray
colorTo: pink
sdk: docker
pinned: false
tags:
  - openenv
  - custom-environment
  - education
---

# 🎓 EduPath AI — Personalized Learning Tutor Environment

> OpenEnv-compliant reinforcement learning environment for training AI agents to be effective personalized tutors.

## 🎯 Motivation

**Why this environment matters for RL/agent research:**

Personalized tutoring is a high-impact, real-world problem. Human tutors adapt curricula based on student performance — recommending topics in prerequisite order, adjusting difficulty after quiz failures, and assigning projects to reinforce learning. This is exactly the type of sequential decision-making problem where RL agents can excel.

EduPath AI provides a **realistic simulation** of this tutoring process across **5 professional domains** (tech, healthcare, business, law, design). Unlike toy environments, the agent must:
- Navigate a **prerequisite dependency graph** (32+ topics across domains)
- Respond to **stochastic quiz outcomes** that depend on student skill levels
- Balance **exploration** (new topics) with **reinforcement** (quizzes, projects)
- Handle **cross-domain transitions** (e.g., a doctor learning AI for healthcare)

This fills a gap in the OpenEnv ecosystem — there are no existing environments modeling **adaptive education**, a domain where AI agents could have immediate, real-world impact.

## 🔥 Key Features

- **Any Field**: Not just tech — works for doctors, lawyers, designers, business professionals
- **Prerequisite Graph**: 32+ topics with dependency ordering across 5 domains
- **Adaptive Quizzes**: Quiz scores depend on skill level; the agent must respond to failures
- **Project Milestones**: Mini-projects and capstone projects award higher rewards
- **Job Readiness Tracking**: Terminal reward when student reaches 80%+ readiness
- **Partial Progress Signals**: 7 distinct reward values, not just binary success/failure

## 📐 Action Space

The agent selects one of 7 action types per step:

| Action | Type | Parameters | Reward Range | Description |
|--------|------|------------|-------------|-------------|
| `recommend_topic` | `string` | `topic_id: str` | +0.3 (good) / -0.2 (prereq fail) / -0.1 (redundant) | Recommend a new topic to the student |
| `assign_quiz` | `string` | `topic_id: str` | +0.2 (pass) / +0.1 (partial) / 0.0 (fail) | Assign a quiz on a topic |
| `assign_mini_project` | `string` | `topic_id: str` | +0.4 (success) / -0.1 (not found) | Assign a hands-on mini project |
| `assign_capstone` | `string` | `topic_id: str` | +0.5 (success) / -0.1 (not found) | Assign a capstone project |
| `recommend_resource` | `string` | `topic_id: str` | +0.1 (found) / 0.0 (none) | Recommend learning resources |
| `suggest_event` | `string` | — | +0.1 | Suggest hackathons or events |
| `mark_job_ready` | `string` | — | +1.0 (terminal, if ≥80%) / -0.2 (premature) | Declare student job-ready |

**Additional penalties:**
- **Loop detection**: -0.1 if the same action type is repeated 3+ times consecutively
- **Episode limit**: 100 steps maximum

## 👁️ Observation Space

Each observation is a Pydantic model (`StudentObservation`) with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `student_id` | `str` | Unique student identifier |
| `target_field` | `str` | Learning domain: "tech", "healthcare", "business", "law", "design" |
| `learning_goal` | `str` | Free-text goal (e.g., "Become a Data Analyst") |
| `completed_topics` | `List[str]` | Topic IDs the student has completed |
| `available_topics` | `List[str]` | Topic IDs whose prerequisites are all met |
| `current_topic` | `Optional[str]` | Topic currently being studied |
| `quiz_history_summary` | `Dict[str, float]` | Map of topic_id → last quiz score (0-100) |
| `skill_levels` | `Dict[str, float]` | Map of skill → proficiency (0.0-1.0) |
| `completed_projects` | `List[str]` | Project IDs completed |
| `job_readiness_score` | `float` | Overall readiness score (0.0-1.0) |
| `badges_earned` | `int` | Number of achievement badges earned |
| `total_steps` | `int` | Steps taken so far in this episode |
| `weekly_hours` | `int` | Student's available study hours per week |

## 📊 OpenEnv Tasks & Baseline Scores

| Task | Difficulty | Scenario | Baseline Score |
|------|------------|----------|---------------|
| `task1_easy` | Easy | Beginner learning Python (5 topics, no prior skills) | **~1.0** |
| `task2_medium` | Medium | Python → Data Analyst + quiz adaptation | **~0.9** |
| `task3_hard` | Hard | Doctor learning AI (cross-domain healthcare→tech) | **~0.8** |

> Scores obtained with the rule-based fallback agent (no LLM). Reproducible via `python inference.py --all` with seed=42.

### Task Details

**Task 1 (Easy):** Agent must sequence 5 Python topics (basics → control flow → OOP → data structures → version control) in correct prerequisite order. Graded on % completed in correct order.

**Task 2 (Medium):** Student knows Python basics, wants to become a Data Analyst. Agent must build a roadmap covering 5 data topics AND adapt when the student fails quizzes. Graded 50% on topic coverage + 50% on quiz performance/adaptation.

**Task 3 (Hard):** A medical doctor with zero tech background wants to learn AI for healthcare. Agent must bridge medicine→tech domains, cover 9+ topics across both fields, and align with a specific job description. Graded 40% job readiness + 30% efficiency + 30% cross-domain bridging.

### Grading Criteria
- **Task 1**: % of expected topics completed in correct prerequisite order (0.0–1.0)
- **Task 2**: Topic coverage (50%) + quiz performance with adaptation (50%)
- **Task 3**: JD skills coverage (40%) + topic efficiency (30%) + cross-domain bridging (30%)

## 🏗️ Architecture

```
EduPath-AI/
├── backend/                  # FastAPI Python backend
│   ├── main.py              # App entry + /reset, /step, /state endpoints
│   ├── environment/         # OpenEnv RL environment
│   │   ├── env.py          # EduPathEnv: step(), reset(), state()
│   │   ├── models.py       # Pydantic: Observation, Action, Reward, StepResult
│   │   ├── curriculum.py   # Multi-field topic graph (32+ topics)
│   │   ├── student.py      # Student state management
│   │   └── graders.py      # Task 1/2/3 graders (0.0-1.0)
│   ├── ai/                  # AI modules (OpenAI Client)
│   │   ├── llm_client.py   # OpenAI-compatible client
│   │   ├── roadmap_generator.py
│   │   └── quiz_generator.py
│   └── api/                 # REST API endpoints
│       ├── onboarding.py   # Student onboarding
│       ├── roadmap.py      # Roadmap generation
│       └── quiz.py         # Adaptive quizzes
├── tasks/                   # OpenEnv task definitions
│   ├── task1_easy.yaml
│   ├── task2_medium.yaml
│   └── task3_hard.yaml
├── inference.py             # Baseline AI agent (OpenAI Client)
├── openenv.yaml             # OpenEnv metadata
├── Dockerfile               # Container definition
└── .env.example             # Environment template
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export API_BASE_URL=https://api.openai.com/v1   # LLM endpoint
export MODEL_NAME=gpt-4o-mini                   # Model name
export HF_TOKEN=your_token_here                 # HuggingFace/API key
```

### 3. Start the Server
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 7860
```

### 4. Run Inference (Baseline Agent)
```bash
# Run all 3 tasks with structured logging
python inference.py --all

# Run a specific task
python inference.py --task task1_easy

# Direct mode (no server needed)
python inference.py --all --direct
```

### 5. Verify OpenEnv Endpoints
```bash
# Reset
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'

# Step
curl -X POST http://localhost:7860/step -H "Content-Type: application/json" \
  -d '{"type": "recommend_topic", "topic_id": "python_basics"}'

# State
curl -X POST http://localhost:7860/state -H "Content-Type: application/json" -d '{}'
```

## 🐳 Docker

```bash
docker build -t edupath-ai .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o-mini \
  -e HF_TOKEN=your_token \
  edupath-ai
```

## 🔌 Reward Function Design

The reward function provides **dense, informative signal** across the full trajectory:

```
+1.0  ── mark_job_ready (terminal, student ≥80% ready)
+0.5  ── assign_capstone (successfully assigned)
+0.4  ── assign_mini_project (successfully assigned)
+0.3  ── recommend_topic (prerequisites met)
+0.2  ── assign_quiz (student passed, score ≥70%)
+0.1  ── assign_quiz (partial, 50-69%) / recommend_resource / suggest_event
 0.0  ── assign_quiz (failed, <50%) / no resources found
-0.1  ── redundant action / unknown topic / loop detected / no project found
-0.2  ── prerequisites not met / premature job_ready
```

This creates a clear **curriculum**: recommend → quiz → (adapt if fail) → project → repeat → job_ready.

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic, Uvicorn
- **AI**: OpenAI Client (API_BASE_URL configurable for any provider)
- **Storage**: In-memory + JSON file persistence (no external DB required)
- **Deploy**: Docker-ready, HuggingFace Spaces compatible (port 7860)
- **Spec**: OpenEnv compliant — `openenv.yaml`, typed models, `/reset`, `/step`, `/state`
