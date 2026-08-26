from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

from schemas.places import PlaceResult, RouteResult, Location


class ChatRequest(BaseModel):
    text: str = Field(..., max_length=500)
    location: Optional[Location] = None
    mode: Optional[str] = "driving"
    session_id: Optional[str] = None
    history: Optional[List[str]] = Field(default_factory=list, max_length=5)

    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in {"driving", "walking", "bicycling"}:
            raise ValueError("Invalid mode")
        return v


class IntentData(BaseModel):
    intent: str = Field(..., description="Main intent: search_places, route, where_am_i,闲聊")
    sub_intent: Optional[str] = None
    search_terms: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    location_hint: Optional[str] = None
    follow_up_to_previous: bool = False
    follow_up_mode: str = "none"
    selected_index: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    places: List[PlaceResult] = Field(default_factory=list)
    directions: List[RouteResult] = Field(default_factory=list)
    session_id: Optional[str] = None
    intent: Optional[IntentData] = None
