from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


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
    selected_index: Optional[int] = None


class PlaceResult(BaseModel):
    name: str
    place_id: Optional[str] = None
    vicinity: Optional[str] = None
    location: Location
    rating: Optional[float] = None
    types: List[str] = Field(default_factory=list)
    source: str = "mapbox"
    distance_km: Optional[float] = None
    maps_deeplink: Optional[str] = None


class RouteStep(BaseModel):
    instruction: str
    distance_text: float
    type: str


class RouteResult(BaseModel):
    origin: Location
    destination: Location
    mode: str = "driving"
    distance_text: float
    duration_text: float
    polyline: Optional[str] = None
    steps: List[RouteStep] = Field(default_factory=list)
    maps_deeplink: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    places: List[PlaceResult] = Field(default_factory=list)
    directions: List[RouteResult] = Field(default_factory=list)
    session_id: Optional[str] = None
    intent: Optional[IntentData] = None


class SessionState(BaseModel):
    session_id: str
    last_user_query: Optional[str] = None
    last_intent: Optional[IntentData] = None
    last_results: List[PlaceResult] = Field(default_factory=list)
    selected_place: Optional[PlaceResult] = None
    current_map_center: Optional[Location] = None
    current_route: Optional[RouteResult] = None