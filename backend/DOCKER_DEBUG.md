# Backend Docker Image Debug Notes

## Context
Building a Docker image for `backend/Dockerfile` to replace ConfigMap-based deployment in Kubernetes.

## Issue
Container fails with: `ModuleNotFoundError: No module named 'api'`

## What the Error Shows
```
File "/app/main.py", line 23, in <module>
    from api import routes_chat, routes_health
ModuleNotFoundError: No module named 'api'
```

## Debugging Findings

### 1. Environment Variables Inside Container
```
PYTHONPATH=/app
```
This is set correctly in Dockerfile.

### 2. Files Inside Container (`/app/`)
Files appear at top-level `/app/` instead of in subdirectories:
```
/app/
  chat.py       # Should be in /app/schemas/chat.py
  config.py     # Should be in /app/utils/config.py
  routes_chat.py # Should be in /app/api/routes_chat.py
  main.py
  ...
```

### 3. Files in Source Directory (backend/)
Structure is correct:
```
backend/
  main.py
  api/
    __init__.py
    routes_chat.py
    routes_health.py
  schemas/
    __init__.py
    chat.py
    places.py
    session.py
  services/
    ...
  providers/
    ...
  utils/
    ...
```

## Dockerfile Content
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py api/ services/ providers/ schemas/ utils/ ./

ENV PYTHONPATH=/app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Build Command
```bash
docker build -t backend:latest /home/khang/projects/AI_chatbox_map/backend
```

## Root Cause Hypothesis
The `COPY` command appears to be flattening directories rather than preserving subdirectory structure. The Docker build context may be incorrectly including files.

## Verification Steps
1. Remove cached Docker build: `docker build --no-cache -t backend:latest backend/`
2. Inspect container filesystem: `docker run --rm backend:latest ls -laR /app/`
3. Check if `api/` subdirectory exists: should see `drwxr-xr-x appuser appuser /app/api/`

## Expected File Structure in Container
```
/app/
  main.py
  api/
    __init__.py
    routes_chat.py
    routes_health.py
  schemas/
    __init__.py
    chat.py
    places.py
    session.py
  services/
    __init__.py
    intent_service.py
    memory_service.py
    ...
  providers/
    __init__.py
    gemini_provider.py
    mapbox_provider.py
  utils/
    __init__.py
    config.py
    polyline.py
```