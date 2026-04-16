"""Health check routes."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Map Chatbot API is running!"}