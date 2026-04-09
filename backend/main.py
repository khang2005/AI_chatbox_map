"""
AI Map Chatbot Backend
----------------------

This FastAPI backend connects your chatbot frontend to Mapbox APIs and Ollama AI.
It handles:
1. Finds nearby places (like "find coffee").
2. Provides directions ("get me to Starbucks").
3. Uses Ollama for AI responses.
"""

import os
import re
from typing import Optional, List, Dict, Tuple
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(title="AI Map Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    mode: Optional[str] = "driving"

# ---------------------------------------------------------------------------
# Helper definitions
# ---------------------------------------------------------------------------

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
    "hotel": "hotel",
    "train station": "rail_station", "subway": "subway", "bus station": "bus_station",
}

ROUTE_TRIGGERS = (
    "get me to", "take me to", "route to", "directions to", "navigate to",
    "drive to", "walk to", "bike to", "nearest", "closest", "near me"
)

ADDRESS_HINT = re.compile(
    r"\d{1,6}\s+[A-Za-z0-9.\- ]+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|way|pkwy|parkway)\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Mapbox API functions
# ---------------------------------------------------------------------------

def normalize_origin(loc) -> Tuple[float, float] | None:
    if not loc:
        return None
    return (loc.lat, loc.lng)

def encode_polyline(coords: List) -> str:
    """Encode a list of [lng, lat] coordinates to a polyline string."""
    result = []
    for coord in coords:
        lng, lat = coord[0], coord[1]
        lat = int(round(lat * 1e5))
        lng = int(round(lng * 1e5))
        dlat = lat - (result[-1] if result else 0)
        dlng = lng - (result[-2] if len(result) > 1 else 0)
        for val in (dlat, dlng):
            val = (val << 1) ^ (val >> 31) if val < 0 else val
            while val >= 0x20:
                result.append(((0x20 | (val & 0x1f)) + 63))
                val >>= 5
            result.append(val + 63)
    return ''.join(chr(c) for c in result)

def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """Decode a polyline string to a list of coordinates."""
    coords = []
    index = 0
    lat = 0
    lng = 0
    while index < len(encoded):
        b = ord(encoded[index]) - 63
        index += 1
        dlat = (b & 0x1f) << 5
        if b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            dlat |= b & 0x1f
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                dlat = (dlat << 5) | (b & 0x1f)
        dlat = (dlat >> 1) ^ -(dlat & 1)
        lat += dlat
        
        b = ord(encoded[index]) - 63
        index += 1
        dlng = (b & 0x1f) << 5
        if b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            dlng |= b & 0x1f
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                dlng = (dlng << 5) | (b & 0x1f)
        dlng = (dlng >> 1) ^ -(dlng & 1)
        lng += dlng
        
        coords.append((lat / 1e5, lng / 1e5))
    return coords

def clean_query(q: str) -> str:
    t = q.lower().strip()
    for trig in ROUTE_TRIGGERS:
        t = t.replace(trig, " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def infer_type_and_keyword(q: str) -> Tuple[str | None, str | None]:
    ql = q.lower()

    # Check for gas station brands first
    for b in GAS_BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", ql):
            return "gas_station", b

    # Category type mapping
    for k, v in TYPE_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", ql):
            extra = ql.replace(k, "").strip()
            # Return the original query for better search results
            return v, q

    return None, q

def search_places(origin: Tuple[float, float], q: str) -> List[dict]:
    """Search for nearby places using Mapbox Search API (for POIs)."""
    t, kw = infer_type_and_keyword(q)
    
    # Build search query
    search_query = kw if kw else q
    if t:
        search_query = f"{search_query} {t}"
    
    # Use Mapbox Search API for places/POIs (different endpoint than geocoding)
    url = "https://api.mapbox.com/search/searchbox/v1/forward"
    params = {
        "access_token": MAPBOX_TOKEN,
        "q": search_query,
        "proximity": f"{origin[1]},{origin[0]}",  # lon,lat
        "limit": 10,
        "session_token": "unique-session-123",  # Helps with results
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        # Check for errors
        if "message" in data:
            print(f"Search API error: {data}")
            results = []
        else:
            results = data.get("features", [])
    except Exception as e:
        print(f"Search API error: {e}")
        results = []

    # Fallback: use geocoding if search fails
    if not results:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(search_query)}.json"
        params = {
            "access_token": MAPBOX_TOKEN,
            "proximity": f"{origin[1]},{origin[0]}",
            "limit": 20,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            results = data.get("features", [])
        except Exception:
            results = []

    # Fallback with larger radius if no results
    if not results:
        results = []
        for r in (10000, 25000, 50000):
            try:
                resp = requests.get(
                    f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(q)}.json",
                    params={"access_token": MAPBOX_TOKEN, "proximity": f"{origin[1]},{origin[0]}", "limit": 20},
                    timeout=10
                )
                data = resp.json()
                results = data.get("features", [])
                if results:
                    break
            except Exception:
                results = []

    out = []
    for r in results[:5]:
        # Geocoding API uses 'center' for coordinates
        lat, lng = None, None
        if "center" in r:
            lat, lng = r["center"][1], r["center"][0]
        elif "geometry" in r and "coordinates" in r["geometry"]:
            lng, lat = r["geometry"]["coordinates"]
        
        if lat is None or lng is None:
            continue
        
        # Get name
        name = r.get("text") or r.get("place_name", "Unknown Place")
        
        # Get vicinity
        vicinity = r.get("place_name", "")
        
        out.append({
            "name": name,
            "place_id": r.get("id"),
            "vicinity": vicinity,
            "location": {"lat": lat, "lng": lng},
            "rating": None,
            "types": [r.get("type")],
        })
    return out

def get_directions(origin: Tuple[float, float], dest: dict, mode="driving"):
    """Get route using Mapbox Directions API."""
    profile_map = {
        "driving": "mapbox/driving",
        "walking": "mapbox/walking",
        "bicycling": "mapbox/cycling",
    }
    profile = profile_map.get(mode, "mapbox/driving")
    
    dest_loc = dest.get("location", {})
    coords = f"{origin[1]},{origin[0]};{dest_loc.get('lng')},{dest_loc.get('lat')}"
    
    url = f"https://api.mapbox.com/directions/v5/{profile}/{coords}"
    params = {
        "access_token": MAPBOX_TOKEN,
        "geometries": "polyline",
        "overview": "full",
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("routes"):
            route = data["routes"][0]
            leg = route["legs"][0]
            steps = [
                {"instruction": s.get("maneuver", {}).get("instruction", ""), "distance_text": s.get("distance")}
                for s in leg.get("steps", [])
            ]
            
            # Handle polyline - could be string or dict
            polyline = route.get("geometry")
            if isinstance(polyline, dict):
                polyline = polyline.get("coordinates")
            
            # Encode coordinates to polyline string if needed
            if isinstance(polyline, list) and len(polyline) > 0:
                polyline = encode_polyline(polyline)
            
            deeplink = (
                f"https://www.mapbox.com/directions/?api=1"
                f"&origin={origin[0]},{origin[1]}"
                f"&destination={dest_loc.get('lat')},{dest_loc.get('lng')}"
                f"&mode={mode}"
            )
            
            return [{
                "origin": {"lat": origin[0], "lng": origin[1]},
                "destination": dest_loc,
                "mode": mode,
                "distance_text": leg.get("distance"),
                "duration_text": leg.get("duration"),
                "polyline": polyline,
                "steps": steps,
                "maps_deeplink": deeplink,
            }]
    except Exception:
        pass
    return []

def is_route_intent(raw: str) -> bool:
    raw = raw.lower()
    route_words = (
        "get me to", "take me to", "route to", "directions to", "navigate to",
        "drive to", "walk to", "bike to", "nearest", "closest", "near me",
        "how to get", "how do i get", "give me directions", "show me the way",
        "navigate", "directions", "route"
    )
    return any(p in raw for p in route_words) or raw.startswith(
        ("take", "get", "navigate", "drive", "walk", "bike", "route")
    )

def reverse_geocode(lat: float, lng: float) -> Optional[str]:
    """Reverse geocode coordinates to address."""
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("features"):
            return data["features"][0].get("place_name")
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Ollama AI functions
# ---------------------------------------------------------------------------

def generate_response(user_query: str, places: List[dict], directions: dict = None) -> str:
    """Generate AI response using Ollama."""
    
    places_info = ""
    if places:
        places_info = "\n".join([
            f"- {p.get('name')} at {p.get('location', {}).get('lat')}, {p.get('location', {}).get('lng')} ({p.get('vicinity')})"
            for p in places[:3]
        ])
    
    route_info = ""
    if directions:
        route_info = f"""
Route found:
- Distance: {directions.get('distance_text')} meters
- Duration: {directions.get('duration_text')} seconds
- Mode: {directions.get('mode')}
"""
    
    prompt = f"""You are a helpful map assistant. Respond to the user's query about locations, places, or directions.

User query: {user_query}

Found places:
{places_info if places_info else "No specific places found nearby."}

{route_info}

Keep responses concise, friendly, and mention the places found.
Response:"""

    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        print(f"Ollama error: {e}")
    
    # Fallback response
    if places:
        names = ", ".join([str(p.get("name") or "Unknown") for p in places[:3]])
        if directions:
            return f"I found {names}. Here's a route: {directions.get('distance_text')}m, {directions.get('duration_text')}s."
        return f"I found these nearby: {names}. Would you like directions?"
    return "Sorry, I couldn't find places for that query. Try enabling location or a different search."

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat(req: ChatReq):
    """Core logic for map-aware chat."""
    raw = (req.text or "").strip()
    if not raw:
        return {"response": "Please enter a request.", "places": [], "directions": []}

    origin = normalize_origin(req.location)
    
    # Handle "where am I" type queries
    lower_raw = raw.lower()
    if any(phrase in lower_raw for phrase in ["where am i", "my location", "current location", "what is my location", "where am located"]):
        if origin:
            address = reverse_geocode(origin[0], origin[1])
            if address:
                return {
                    "response": f"You are at: {address}",
                    "places": [],
                    "directions": [],
                }
            return {
                "response": f"Your coordinates are: {origin[0]}, {origin[1]}",
                "places": [],
                "directions": [],
            }
        return {
            "response": "Please enable location access so I can tell you where you are.",
            "places": [],
            "directions": [],
        }
    
    if not origin:
        return {
            "response": "Please enable location access so I can help you navigate.",
            "places": [],
            "directions": [],
        }

    route_mode = req.mode or "driving"
    wants_route = is_route_intent(raw)
    cleaned = clean_query(raw)

    # Try address lookup first
    direct = None
    if ADDRESS_HINT.search(cleaned):
        direct = geocode_address(cleaned)
    
    places = [direct] if direct else search_places(origin, cleaned)

    if not places:
        return {"response": f"I couldn't find anything for '{cleaned}'.", "places": [], "directions": []}

    # Route logic
    if wants_route and places:
        dest = places[0]
        directions = get_directions(origin, dest, mode=route_mode)
        
        if directions:
            response_text = generate_response(raw, places, directions[0])
            return {
                "response": response_text,
                "places": [dest],
                "directions": directions,
            }
        
        return {"response": f"I couldn't find a route to {dest['name']}.", "places": [dest], "directions": []}

    # Nearby places logic
    for p in places:
        loc = p.get("location", {})
        p["maps_deeplink"] = f"https://www.mapbox.com/search/?api=1&query={loc.get('lat')},{loc.get('lng')}"

    response_text = generate_response(raw, places)
    return {
        "response": response_text,
        "places": places,
        "directions": [],
    }

@app.get("/")
async def root():
    return {"message": "AI Map Chatbot API is running with Mapbox + Ollama!"}

# ---------------------------------------------------------------------------
# Local run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
