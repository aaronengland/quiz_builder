# ==========================
# Stage 1: Build React frontend
# ==========================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package*.json ./
RUN npm install --no-audit --progress=false

# Copy source and build production assets
COPY frontend/ ./
RUN npm run build


# ==========================
# Stage 2: Build Python backend (FastAPI)
# ==========================
FROM python:3.11-slim AS backend

# Prevent Python from writing .pyc files & buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy and install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./

# Copy built frontend assets into the container (FastAPI serves these)
COPY --from=frontend-builder /app/frontend/dist ./frontend_build

# Expose port (ECS Express compatible)
EXPOSE 5000

# Run FastAPI with gunicorn + uvicorn workers (production)
CMD ["gunicorn", "main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "300", \
     "--keep-alive", "65", \
     "--access-logfile", "-"]
