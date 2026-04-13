"""
AI Map Chatbot Backend
----------------------

This FastAPI backend connects your chatbot frontend to Mapbox APIs and Gemini AI.
It handles:
1. Finds nearby places (like "find coffee").
2. Provides directions ("get me to Starbucks").
3. Uses Gemini for AI responses with agentic RAG architecture.
"""

import os
import re
from typing import Optional, List, Tuple
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    "get me to", "take me to", "route to", "directions to", "navigate to", "navigate me to",
    "drive to", "walk to", "bike to", "nearest", "closest", "near me", "nearby",
    "find", "search for", "look for", "where is", "show me", "take me"
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
    # Clean up common stopwords
    t = re.sub(r"\b(a|an|the|to|in|of|for|with)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    print(f"DEBUG clean_query: '{q}' -> '{t}'")
    return t

def search_places_nominatim(origin: Tuple[float, float], q: str) -> List[dict]:
    """Search for nearby places using Nominatim (OpenStreetMap) - free & reliable."""
    lat, lon = origin[0], origin[1]
    
    # Define a bounding box around the user (approx 10km radius)
    lat_min, lat_max = lat - 0.1, lat + 0.1
    lon_min, lon_max = lon - 0.1, lon + 0.1
    
    params = {
        "q": q,
        "format": "json",
        "limit": 10,
        "viewbox": f"{lon_min},{lat_min},{lon_max},{lat_max}",
        "bounded": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": "AI-Map-Chatbox/1.0"}
    
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=headers,
            timeout=10
        )
        results = resp.json()
        
        # If bounded search fails, try without bounds
        if not results:
            params = {
                "q": f"{q} near {lat},{lon}",
                "format": "json",
                "limit": 10,
                "addressdetails": 1,
            }
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
                timeout=10
            )
            results = resp.json()
        
        out = []
        if isinstance(results, list):
            for r in results[:5]:
                lat_val = float(r.get("lat", 0))
                lon_val = float(r.get("lon", 0))
                if lat_val == 0 or lon_val == 0:
                    continue
                
                # Get name from display_name (first part)
                display_name = r.get("display_name", "Unknown")
                name = display_name.split(",")[0] if display_name else "Unknown"
                
                # Get vicinity from address
                address_parts = r.get("address", {})
                city = address_parts.get("city") or address_parts.get("town") or address_parts.get("county") or ""
                road = address_parts.get("road") or ""
                vicinity = f"{road}, {city}".strip(", ") if city else road
                
                out.append({
                    "name": name,
                    "place_id": r.get("place_id"),
                    "vicinity": vicinity or display_name.split(",")[0],
                    "location": {"lat": lat_val, "lng": lon_val},
                    "rating": None,
                    "types": [r.get("type")],
                    "source": "nominatim",
                })
        return out
    except Exception as e:
        print(f"Nominatim error: {e}")
        return []

def infer_type_and_keyword(q: str) -> Tuple[str | None, str | None]:
    ql = q.lower()

    # Check for gas station brands first
    for b in GAS_BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", ql):
            return "gas_station", b

    # Category type mapping
    for k, v in TYPE_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", ql):
            return v, q

    return None, q

def search_places(origin: Tuple[float, float], q: str) -> List[dict]:
    """Search for nearby places using Mapbox (primary) with Nominatim fallback."""
    t, kw = infer_type_and_keyword(q)
    
    search_query = q.strip()
    
    url = "https://api.mapbox.com/search/searchbox/v1/forward"
    params = {
        "access_token": MAPBOX_TOKEN,
        "q": search_query,
        "proximity": f"{origin[1]},{origin[0]}",
        "limit": 10,
        "language": "en",
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if "message" in data:
            print(f"Mapbox Search error: {data}")
            results = []
        else:
            results = data.get("features", [])
    except Exception as e:
        print(f"Mapbox Search error: {e}")
        results = []

    # Filter to only POIs and nearby results (within ~30km)
    filtered = []
    origin_lat, origin_lon = origin[0], origin[1]
    print(f"DEBUG: origin={origin_lat},{origin_lon}")
    for r in results[:10]:
        geom = r.get("geometry", {})
        coords = geom.get("coordinates", [])
        if not coords:
            continue
        res_lng, res_lat = coords[0], coords[1]
        # Calculate rough distance
        dist = ((res_lng - origin_lon)**2 + (res_lat - origin_lat)**2) ** 0.5 * 111  # approx km
        print(f"DEBUG: {r.get('properties',{}).get('name')} at {res_lat},{res_lng} = {dist:.1f}km, type={r.get('properties',{}).get('feature_type')}")
        if dist > 30:
            continue
        # Prefer POIs over streets
        r["_dist"] = dist
        r["_is_poi"] = r.get("properties", {}).get("feature_type") == "poi"
        filtered.append(r)
    
    # If no POIs found within 30km, do a fallback search with simpler query
    if not filtered:
        print("DEBUG: No nearby results, trying fallback search...")
        simple_q = " ".join(q.split()[:2])
        if simple_q:
            url2 = "https://api.mapbox.com/search/searchbox/v1/forward"
            params2 = {
                "access_token": MAPBOX_TOKEN,
                "q": simple_q,
                "proximity": f"{origin[1]},{origin[0]}",
                "limit": 10,
                "language": "en",
            }
            try:
                resp2 = requests.get(url2, params=params2, timeout=10)
                data2 = resp2.json()
                results2 = data2.get("features", [])
                print(f"DEBUG: Fallback search returned {len(results2)} results")
                for r in results2[:10]:
                    geom = r.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if not coords:
                        continue
                    res_lng, res_lat = coords[0], coords[1]
                    dist = ((res_lng - origin_lon)**2 + (res_lat - origin_lat)**2) ** 0.5 * 111
                    if dist <= 30:
                        r["_dist"] = dist
                        r["_is_poi"] = r.get("properties", {}).get("feature_type") == "poi"
                        filtered.append(r)
            except Exception as e:
                print(f"DEBUG: Fallback search error: {e}")
    
    # Sort: POIs first, then by distance (handle empty list)
    if filtered:
        filtered.sort(key=lambda x: (not x.get("_is_poi", False), x.get("_dist", float("inf"))))
        results = filtered[:5]
    else:
        results = []
    
    out = []
    for r in results:
        props = r.get("properties", {})
        
        # Get name - prefer poi name, fallback to address
        name = props.get("name") or r.get("text") or "Unknown Place"
        
        # Get coordinates
        geom = r.get("geometry", {})
        coords = geom.get("coordinates", [])
        if isinstance(coords, list) and len(coords) == 2:
            lng, lat = coords[0], coords[1]
        else:
            continue
        
        # Get vicinity - prefer full address
        address = props.get("address") or ""
        full_address = props.get("full_address") or ""
        place_name = r.get("place_name") or ""
        vicinity = full_address or address or place_name
        
        out.append({
            "name": name,
            "place_id": props.get("mapbox_id") or r.get("id"),
            "vicinity": vicinity,
            "location": {"lat": lat, "lng": lng},
            "rating": None,
            "types": [r.get("type")],
            "source": "mapbox",
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
        "steps": "true",
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("routes"):
            route = data["routes"][0]
            leg = route["legs"][0]
            steps = []
            for s in leg.get("steps", []):
                maneuver = s.get("maneuver", {})
                banner = s.get("bannerInstructions", [])
                
                # Prefer banner instruction, fall back to maneuver
                instruction = ""
                if banner and len(banner) > 0:
                    instruction = banner[0].get("primary", {}).get("text", "")
                if not instruction:
                    maneuver_type = maneuver.get("type", "")
                    instruction = maneuver.get("instruction", "")
                    if not instruction and maneuver_type:
                        instruction = f"{maneuver_type.replace('_', ' ').title()}"
                
                steps.append({
                    "instruction": instruction,
                    "distance_text": s.get("distance"),
                    "type": maneuver.get("type", "")
                })
            
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
    raw_lower = raw.lower()
    route_words = (
        "get me to", "take me to", "route to", "directions to", "navigate to",
        "drive to", "walk to", "bike to", "nearest", "closest", "near me",
        "how to get", "how do i get", "give me directions", "show me the way",
        "navigate", "directions", "route"
    )
    # Check for full phrases first
    for phrase in route_words:
        if phrase in raw_lower:
            return True
    # Then check single words with word boundary
    single_words = ("take", "get", "navigate", "drive", "walk", "bike", "route")
    for word in single_words:
        if re.search(rf"\b{word}\b", raw_lower):
            return True
    return False

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
# Gemini AI functions
# ---------------------------------------------------------------------------

def generate_response(user_query: str, places: List[dict], directions: dict = None) -> str:
    """Generate AI response using Gemini."""
    
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

Keep responses concise, friendly, and mention the places found. If directions are available, mention them.
Response:"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
    
    # Fallback response without AI
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

    places = search_places(origin, cleaned)

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
    return {"message": "AI Map Chatbot API is running with Mapbox + Gemini!"}

# ---------------------------------------------------------------------------
# Local run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
