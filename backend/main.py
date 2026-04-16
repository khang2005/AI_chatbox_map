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
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import routes_chat, routes_health
from utils.config import MAPBOX_TOKEN, GEMINI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
