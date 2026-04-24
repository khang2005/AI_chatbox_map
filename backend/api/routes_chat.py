"""Chat API routes."""
import logging
import time
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from schemas.chat import ChatRequest, ChatResponse
from services.memory_service import get_memory_service
from services.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

_memory_service = get_memory_service(persist_path="data/session_memory.json")

router = APIRouter(prefix="/api", tags=["chat"])

_rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60


def get_client_ip(request: Request) -> str:
    """Get client IP, considering reverse proxy."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP is rate limited."""
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
    ip_requests = _rate_limit_store[ip]
    valid_requests = [req_time for req_time in ip_requests if req_time > window_start]
    _rate_limit_store[ip] = valid_requests
    
    if len(valid_requests) >= RATE_LIMIT_REQUESTS:
        return False
    
    _rate_limit_store[ip].append(current_time)
    return True


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, req: ChatRequest) -> dict:
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
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "rate_limit_exceeded"}
        )
    
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
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error"}
        )