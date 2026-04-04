FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY inference.py .
COPY gym_wrapper.py .
COPY train.py .
COPY evaluate.py .
COPY tasks/ ./tasks/
COPY openenv.yaml .
COPY README.md .
# Copy trained models and results (create dirs if absent)
RUN mkdir -p ./models ./results

# Required env vars (set at runtime)
ENV API_BASE_URL=""
ENV MODEL_NAME="gpt-4o-mini"
ENV HF_TOKEN=""
ENV PYTHONPATH="/app/backend"

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Run from /app so both backend and inference.py are accessible
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
