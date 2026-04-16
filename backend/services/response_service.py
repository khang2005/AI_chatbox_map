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
        return self.gemini.generate_response(
            user_query=user_query,
            places=places,
            directions=directions,
            intent=intent
        )

    def generate_where_am_i(self, address: str) -> str:
        return f"You are at: {address}"

    def generate_error(self, error_type: str) -> str:
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
        context: dict,
        is_result_reference: bool = False
    ) -> str:
        if is_result_reference:
            selected_place = context.get("selected_place")
            selected_place_name = (
                selected_place.get("name")
                if isinstance(selected_place, dict)
                else None
            )
            
            return self.gemini.generate_response(
                user_query=query,
                places=context.get("last_results", [])[:3],
                directions=context.get("current_route"),
                intent={
                    "intent": "follow_up",
                    "context": {
                        "last_query": context.get("last_user_query"),
                        "selected_place": selected_place_name,
                        "last_results_count": len(context.get("last_results", []))
                    }
                }
            )
        
        return self.gemini.generate_response(
            user_query=query,
            places=[],
            directions=None,
            intent={"intent": "general_chat"}
        )


_response_service: Optional[ResponseService] = None


def get_response_service() -> ResponseService:
    global _response_service
    if _response_service is None:
        _response_service = ResponseService()
    return _response_service
