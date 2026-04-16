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
