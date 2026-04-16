"""Response service - generates natural language responses."""
import logging
from typing import Optional, List, Dict, Any

from providers.gemini_provider import get_gemini_provider

logger = logging.getLogger(__name__)


class ResponseService:
    """Service for generating user-facing responses."""

    def __init__(self):
        self.gemini = get_gemini_provider()

    def generate(
        self,
        user_query: str,
        places: List[dict],
        directions: Optional[dict] = None,
        intent: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate natural language response.
        
        Args:
            user_query: Original user query
            places: List of found places
            directions: Optional route info
            intent: Structured intent data
            
        Returns:
            Response string
        """
        return self.gemini.generate_response(
            user_query=user_query,
            places=places,
            directions=directions,
            intent=intent
        )

    def generate_where_am_i(self, address: str) -> str:
        """Generate response for where am I query."""
        return f"You are at: {address}"

    def generate_error(self, error_type: str) -> str:
        """Generate error response."""
        errors = {
            "no_location": "Please enable location access so I can help you navigate.",
            "no_results": "Sorry, I couldn't find any places matching your request.",
            "no_route": "I couldn't find a route to that location.",
            "api_error": "Sorry, something went wrong. Please try again.",
        }
        return errors.get(error_type, "An error occurred. Please try again.")

    def generate_follow_up(
        self,
        query: str,
        context: dict
    ) -> str:
        """Generate response for follow-up queries."""
        session_context = {
            "last_query": context.get("last_query"),
            "last_intent": context.get("last_intent"),
            "last_results_count": len(context.get("last_results", [])),
            "selected_place": context.get("selected_place", {}).get("name") if context.get("selected_place") else None,
        }
        
        # Use Gemini for follow-up with context
        return self.gemini.generate_response(
            user_query=query,
            places=context.get("last_results", [])[:3],
            directions=context.get("current_route"),
            intent={"intent": "follow_up", "context": session_context}
        )


# Singleton
_response_service: Optional[ResponseService] = None


def get_response_service() -> ResponseService:
    global _response_service
    if _response_service is None:
        _response_service = ResponseService()
    return _response_service