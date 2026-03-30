# 🎓 EduPath AI — Personalized Learning Tutor Environment

> OpenEnv-compliant reinforcement learning environment for personalized AI tutoring.

## 🔥 What is EduPath AI?

EduPath AI is an AI-powered learning platform that generates **fully personalized learning roadmaps for any field** — tech, healthcare, law, business, design. It adapts in real-time based on quiz performance, assigns projects, awards badges, and tracks job readiness.

### Key Differentiators
- **Any Field**: Not just tech — works for doctors, lawyers, designers, business professionals
- **Smart Onboarding**: 2-minute setup with resume parsing and granular skill assessment
- **Live Resource Fetching**: Automatically fetches and caches high-quality free courses via DuckDuckGo Search API.
- **Adaptive**: Quizzes adapt based on scores (≥70% → advance, 50-70% → review, <50% → restart)
- **No YouTube**: Uses structured resources (MIT OCW, Kaggle, fast.ai, official docs, freeCodeCamp)
- **OpenEnv Compliant**: Full RL environment with step/reset/state, reward signals, and graders

## 🏗️ Architecture

```
EduPath-AI/
├── backend/                  # FastAPI Python backend
│   ├── main.py              # App entry point
│   ├── environment/         # OpenEnv RL environment
│   │   ├── env.py          # step(), reset(), state()
│   │   ├── models.py       # Pydantic data models
│   │   ├── curriculum.py   # Multi-field topic graph
│   │   ├── student.py      # Student state management
│   │   └── graders.py      # Task 1/2/3 graders (0.0-1.0)
│   ├── ai/                  # AI modules (OpenAI Client)
│   │   ├── llm_client.py   # OpenAI-compatible client
│   │   ├── roadmap_generator.py
│   │   ├── quiz_generator.py
│   │   └── resume_parser.py
│   └── api/                 # REST API endpoints
│       ├── onboarding.py   # 4-step onboarding
│       ├── roadmap.py      # Roadmap generation
│       ├── quiz.py         # Adaptive quizzes
│       ├── badges.py       # Achievement system
│       └── career.py       # Job readiness
├── frontend/                # Next.js TypeScript frontend
│   └── app/
│       ├── page.tsx        # Landing page
│       ├── onboarding/     # 4-step wizard
│       └── dashboard/      # Main dashboard
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

### Backend
```bash
cd backend
pip install -r requirements.txt
# Set required env vars
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=your_token_here
# Run
python -m uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Run Inference (Baseline Agent)
```bash
# Run all tasks
python inference.py --all

# Run a specific task
python inference.py --task 1
```

### Environment Variables
```
API_BASE_URL=https://api.openai.com/v1     # Required: LLM endpoint
MODEL_NAME=gpt-4o-mini                     # Required: Model name
HF_TOKEN=your_hf_token                     # Required: HuggingFace token
NEXT_PUBLIC_API_URL=http://localhost:8000   # Frontend API URL
```

## 📊 OpenEnv Tasks & Baseline Scores

| Task | Difficulty | Scenario | Baseline Score |
|------|------------|----------|---------------|
| Task 1 | Easy | Beginner learning Python (5 topics) | **1.0000** |
| Task 2 | Medium | Python → Data Analyst + quiz adaptation | **0.9127** |
| Task 3 | Hard | Doctor learning AI (cross-domain healthcare) | **0.8235** |

> Scores obtained with the rule-based fallback agent (no LLM).
> Reproducible via `python inference.py --all` with seed=42.

### Grading Criteria
- **Task 1**: % of expected topics completed in correct prerequisite order
- **Task 2**: Topic coverage (50%) + quiz performance with adaptation (50%)
- **Task 3**: JD skills coverage (40%) + topic efficiency (30%) + cross-domain bridging (30%)

## 🐳 Docker

```bash
docker build -t edupath-ai .
docker run -p 8000:8000 \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o-mini \
  -e HF_TOKEN=your_token \
  edupath-ai
```

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic, Uvicorn
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **AI**: OpenAI Client (API_BASE_URL configurable)
- **Storage**: JSON file persistence (no external DB)
- **Deploy**: Docker-ready, HuggingFace Spaces compatible
