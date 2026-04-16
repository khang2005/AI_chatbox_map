from pydantic import BaseModel, Field
from typing import Optional, List


class Location(BaseModel):
    lat: float
    lng: float


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
