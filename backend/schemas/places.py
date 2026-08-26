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
    review_count: Optional[int] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    price: Optional[str] = None
    is_open: Optional[bool] = None
    brand: Optional[str] = None
    poi_categories: List[str] = Field(default_factory=list)
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