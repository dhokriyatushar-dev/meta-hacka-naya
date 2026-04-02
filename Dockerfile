FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY inference.py .
COPY tasks/ ./tasks/
COPY openenv.yaml .
COPY README.md .

# Set working directory for backend
WORKDIR /app/backend

# Required env vars (set at runtime)
ENV API_BASE_URL=""
ENV MODEL_NAME="gpt-4o-mini"
ENV HF_TOKEN=""

# Hugging Face Spaces requires port 7860
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
