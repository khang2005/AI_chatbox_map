"""Memory service - stores session state for follow-up queries."""
import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class MemoryService:
    """In-memory storage for session state to support follow-up queries."""

    def __init__(self):
        # session_id -> state dict
        self._sessions: Dict[str, dict] = {}

    def get_session(self, session_id: str) -> dict:
        """Get or create session state."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "last_query": None,
                "last_intent": None,
                "last_results": [],
                "selected_place": None,
                "current_map_center": None,
                "current_route": None,
            }
        return self._sessions[session_id]

    def update(
        self,
        session_id: str,
        last_query: Optional[str] = None,
        last_intent: Optional[dict] = None,
        last_results: Optional[List[dict]] = None,
        selected_place: Optional[dict] = None,
        current_map_center: Optional[dict] = None,
        current_route: Optional[dict] = None,
    ):
        """Update session state."""
        session = self.get_session(session_id)
        
        if last_query is not None:
            session["last_query"] = last_query
        if last_intent is not None:
            session["last_intent"] = last_intent
        if last_results is not None:
            session["last_results"] = last_results
        if selected_place is not None:
            session["selected_place"] = selected_place
        if current_map_center is not None:
            session["current_map_center"] = current_map_center
        if current_route is not None:
            session["current_route"] = current_route

    def get_context(self, session_id: str) -> dict:
        """Get context from session for follow-up processing."""
        return self.get_session(session_id)

    def clear_session(self, session_id: str):
        """Clear a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# Singleton
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service