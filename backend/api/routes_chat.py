"""Chat API routes."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from schemas.chat import ChatRequest, ChatResponse
from services.memory_service import get_memory_service
from services.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

_memory_service = get_memory_service(persist_path="data/session_memory.json")

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> dict:
    """
    Handle chat requests.
    
    Pipeline:
    1. Extract intent (Gemini)
    2. Rewrite query
    3. Search places
    4. Rank results
    5. Get route (if needed)
    6. Generate response
    """
    orchestrator = get_orchestrator()
    
    try:
        result = orchestrator.handle(
            query=req.text,
            location=req.location.model_dump() if req.location else None,
            mode=req.mode or "driving",
            session_id=req.session_id or "default"
        )
        return result
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))