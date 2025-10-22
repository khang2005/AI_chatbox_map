"""
AI Map Chatbot Backend
----------------------

This FastAPI backend connects your chatbot frontend to Google Maps APIs.
It handles three main functions:
1. Finds nearby places (like "find coffee").
2. Provides directions ("get me to Starbucks").
3. Returns clean structured JSON for the frontend to render markers and routes.
"""

import os
import re
from typing import Optional, List, Dict, Tuple
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import googlemaps
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_KEY)

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(title="AI Map Chatbot API")

# Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Location(BaseModel):
    lat: float
    lng: float

class ChatReq(BaseModel):
    text: str
    location: Optional[Location] = None
    mode: Optional[str] = "driving"  # driving|walking|bicycling|transit

# ---------------------------------------------------------------------------
# Helper definitions
# ---------------------------------------------------------------------------

# Common categories and brands
GAS_BRANDS = {
    "arco", "shell", "chevron", "76", "bp", "exxon", "mobil", "marathon",
    "valero", "costco", "speedway", "sunoco", "phillips 66",
    "circle k", "conoco", "texaco"
}

TYPE_MAP = {
    "gas station": "gas_station", "gas": "gas_station", "fuel": "gas_station",
    "coffee": "cafe", "cafe": "cafe",
    "pharmacy": "pharmacy",
    "restaurant": "restaurant",
    "grocery": "supermarket", "supermarket": "supermarket",
    "bank": "bank", "atm": "atm",
    "hotel": "lodging", "lodging": "lodging",
    "train station": "train_station", "subway": "subway_station", "bus station": "bus_station",
}

# Common route keywords
ROUTE_TRIGGERS = (
    "get me to", "take me to", "route to", "directions to", "navigate to",
    "drive to", "walk to", "bike to", "nearest", "closest", "near me"
)

# Detect if user typed a full address
ADDRESS_HINT = re.compile(
    r"\d{1,6}\s+[A-Za-z0-9.\- ]+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|way|pkwy|parkway)\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalize_origin(loc) -> Tuple[float, float] | None:
    """Converts the Location model to a (lat, lng) tuple."""
    if not loc:
        return None
    return (loc.lat, loc.lng)

def clean_query(q: str) -> str:
    """Removes trigger words like 'get me to' or 'find'."""
    t = q.lower().strip()
    for trig in ROUTE_TRIGGERS:
        t = t.replace(trig, " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def infer_type_and_keyword(q: str) -> Tuple[str | None, str | None]:
    """Figures out what type of place the user is referring to."""
    ql = q.lower()

    # Known brands (for gas stations)
    for b in GAS_BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", ql):
            return "gas_station", b

    # Category type (like "coffee" → cafe)
    for k, v in TYPE_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", ql):
            extra = ql.replace(k, "").strip()
            if extra and extra not in {"near", "me", "now"}:
                return v, q
            return v, None

    # Default
    return None, q

# ---------------------------------------------------------------------------
# Google Maps API helpers
# ---------------------------------------------------------------------------

def places_search(origin: Tuple[float, float], q: str) -> List[dict]:
    """Search for nearby places or use text search if none found."""
    t, kw = infer_type_and_keyword(q)
    nearby_kwargs = dict(location=origin, rank_by="distance")
    if t:
        nearby_kwargs["type"] = t
    if kw:
        nearby_kwargs["keyword"] = kw

    try:
        resp = gmaps.places_nearby(**nearby_kwargs)
        results = resp.get("results", [])
    except Exception:
        results = []

    # Fallback: text search with radius if nothing found
    if not results:
        for r in (10000, 25000, 50000):
            try:
                resp = gmaps.places(query=q, location=origin, radius=r)
                results = resp.get("results", [])
                if results:
                    break
            except Exception:
                results = []

    # Normalize results
    out = []
    for r in results[:5]:
        loc = (r.get("geometry") or {}).get("location", {})
        out.append({
            "name": r.get("name"),
            "place_id": r.get("place_id"),
            "vicinity": r.get("vicinity"),
            "location": {"lat": loc.get("lat"), "lng": loc.get("lng")},
            "rating": r.get("rating"),
            "types": r.get("types"),
        })
    return out

def maybe_find_place(q: str, origin: Tuple[float, float]):
    """If the query looks like an address, use 'Find Place' API."""
    if ADDRESS_HINT.search(q):
        try:
            fp = gmaps.find_place(
                input=q,
                input_type="textquery",
                fields=["place_id", "name", "geometry", "formatted_address"]
            )
            cands = fp.get("candidates", [])
            if cands:
                c = cands[0]
                return {
                    "name": c.get("name") or c.get("formatted_address"),
                    "place_id": c.get("place_id"),
                    "vicinity": c.get("formatted_address"),
                    "location": (c.get("geometry") or {}).get("location"),
                }
        except Exception:
            pass
    return None

def get_directions(origin: Tuple[float, float], place_id: str, mode="driving"):
    """Uses Google Directions API to get route data."""
    try:
        return gmaps.directions(origin, f"place_id:{place_id}", mode=mode)
    except Exception:
        return []

def is_route_intent(raw: str) -> bool:
    """Checks if user message sounds like a request for directions."""
    raw = raw.lower()
    return any(p in raw for p in ROUTE_TRIGGERS) or raw.startswith(
        ("take", "get", "navigate", "drive", "walk", "bike", "route", "directions")
    )

# ---------------------------------------------------------------------------
# /api/chat Endpoint
# ---------------------------------------------------------------------------
# ---------- /api/chat ----------
@app.post("/api/chat")
def chat(req: ChatReq):
    """
    Core logic for map-aware chat.
    It figures out if the user wants directions or just nearby search,
    then returns structured data for the frontend map.
    """
    raw = (req.text or "").strip()
    if not raw:
        return {"response": "Please enter a request.", "places": [], "directions": []}

    origin = normalize_origin(req.location)
    if not origin:
        return {
            "response": "Please enable location access so I can help you navigate.",
            "places": [],
            "directions": [],
        }

    route_mode = req.mode or "driving"
    wants_route = is_route_intent(raw)
    cleaned = clean_query(raw)

    # Try exact match first, then general search
    direct = maybe_find_place(cleaned, origin)
    places = [direct] if direct else places_search(origin, cleaned)

    if not places:
        return {"response": f"I couldn’t find anything for '{cleaned}'.", "places": [], "directions": []}

    # ---------- Route logic ----------
    if wants_route and places:
        dest = places[0]
        dest_loc = dest.get("location")
        gdirs = get_directions(origin, dest.get("place_id"), mode=route_mode)

        if gdirs:
            leg = gdirs[0]["legs"][0]
            steps = [
                {"instruction": s.get("html_instructions", ""), "distance_text": s.get("distance", {}).get("text")}
                for s in leg.get("steps", [])
            ]
            polyline = gdirs[0].get("overview_polyline", {}).get("points")

            deeplink = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={origin[0]},{origin[1]}"
                f"&destination={dest_loc.get('lat')},{dest_loc.get('lng')}"
                f"&travelmode={route_mode}"
            )

            directions = [{
                "origin": {"lat": origin[0], "lng": origin[1]},
                "destination": dest_loc,
                "mode": route_mode,
                "distance_text": leg.get("distance", {}).get("text"),
                "duration_text": leg.get("duration", {}).get("text"),
                "polyline": polyline,
                "steps": steps,
                "maps_deeplink": deeplink,
            }]

            response_text = (
                f"Okay! Here’s the best route to {dest['name']} "
                f"({dest.get('vicinity','unknown address')}): "
                f"{leg.get('duration', {}).get('text')} ({leg.get('distance', {}).get('text')})."
            )

            return {
                "response": response_text,
                "places": [dest],
                "directions": directions,
            }

        return {"response": f"I couldn’t find a route to {dest['name']}.", "places": [dest], "directions": []}

    # ---------- Nearby places logic ----------
    for p in places:
        loc = p.get("location", {})
        p["maps_deeplink"] = f"https://www.google.com/maps/search/?api=1&query={loc.get('lat')},{loc.get('lng')}"

    names = ", ".join([p["name"] for p in places[:3]])
    return {
        "response": f"Here are nearby matches: {names}.",
        "places": places,
        "directions": [],
    }

# ---------------------------------------------------------------------------
# Root health check
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "AI Map Chatbot API is running!"}

# ---------------------------------------------------------------------------
# Local run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

