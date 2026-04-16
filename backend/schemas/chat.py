from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from schemas.places import PlaceResult, RouteResult


class Location(BaseModel):
    lat: float
    lng: float


class ChatRequest(BaseModel):
    text: str
    location: Optional[Location] = None
    mode: Optional[str] = "driving"
    session_id: Optional[str] = None


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
