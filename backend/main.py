"""
AI Map Chatbot Backend
----------------------

FastAPI backend connecting frontend to Mapbox and Gemini.
Refactored to use clean modular architecture.

Architecture:
- api/          - Route handlers
- schemas/      - Pydantic models
- services/     - Business logic (orchestrator, ranking, etc.)
- providers/    - External API wrappers (Gemini, Mapbox)
- utils/        - Utilities (config, polyline)
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import routes_chat, routes_health
from utils.config import MAPBOX_TOKEN, GEMINI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


def get_client_ip(request: Request) -> str:
    """Get client IP, considering reverse proxy."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class LogRequestsMiddleware(BaseHTTPMiddleware):
    """Log request IP, timestamp, and endpoint."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = get_client_ip(request)
        
        logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
        
        return response


class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    """Reject large request bodies."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1024 * 1024:  # 1MB
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "request_too_large"}
            )
        
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI Map Chatbot API")
    
    if not MAPBOX_TOKEN:
        logger.warning("MAPBOX_ACCESS_TOKEN not set")
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set")
    
    yield
    logger.info("Shutting down AI Map Chatbot API")


app = FastAPI(
    title="AI Map Chatbot API",
    description="Map assistant with Gemini intent extraction and Mapbox routing",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(LimitRequestSizeMiddleware)
app.add_middleware(LogRequestsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_chat.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
