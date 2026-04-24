from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionSearchContext(BaseModel):
    last_category: Optional[str] = None
    last_area_name: Optional[str] = None
    last_action: Optional[str] = None


class SessionMemory(BaseModel):
    session_id: str
    last_user_query: Optional[str] = None
    last_intent: Dict[str, Any] = Field(default_factory=dict)
    last_results: List[Dict[str, Any]] = Field(default_factory=list)
    selected_place: Optional[Dict[str, Any]] = None
    current_route: Optional[Dict[str, Any]] = None
    last_origin: Optional[Dict[str, float]] = None
    search_context: SessionSearchContext = Field(default_factory=SessionSearchContext)
    updated_at: float = 0.0

    def get_conversation_history(self, max_messages: int = 5) -> List[Dict[str, Any]]:
        """Get trimmed conversation history for token control."""
        history = []
        
        if self.last_user_query and self.last_intent:
            history.append({
                "role": "user",
                "content": self.last_user_query,
                "timestamp": self.updated_at
            })
        
        # Keep only the most recent messages
        return history[-max_messages:] if max_messages > 0 else history

    def trim_context_for_llm(self) -> Dict[str, Any]:
        """Get trimmed context for LLM calls to reduce token usage."""
        context = self.model_dump()
        
        # Limit last results to top 3
        if "last_results" in context and context["last_results"]:
            context["last_results"] = context["last_results"][:3]
        
        # Remove unnecessary fields
        context.pop("updated_at", None)
        context.pop("session_id", None)
        
        return context
