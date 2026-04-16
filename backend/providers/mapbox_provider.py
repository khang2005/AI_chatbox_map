"""Mapbox API provider for place search, routing, and geocoding."""
import logging
import math
from typing import Optional, List, Tuple

import requests

from utils.config import get_mapbox_token

logger = logging.getLogger(__name__)


class MapboxProvider:
    """Wrapper for Mapbox APIs: Search, Directions, Geocoding."""

    def __init__(self):
        self.token = get_mapbox_token()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AI-Map-Chatbox/1.0"})

    def search_places(
        self,
        query: str,
        origin: Tuple[float, float],
        limit: int = 10
    ) -> List[dict]:
        """Search for places using Mapbox Search API."""
        
        url = "https://api.mapbox.com/search/searchbox/v1/forward"
        params = {
            "access_token": self.token,
            "q": query,
            "proximity": f"{origin[1]},{origin[0]}",  # lon,lat
            "limit": limit,
            "language": "en",
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if "message" in data:
                logger.error(f"Mapbox Search error: {data}")
                return []
            
            return data.get("features", [])
            
        except Exception as e:
            logger.error(f"Mapbox Search exception: {e}")
            return []

    def filter_nearby(
        self,
        results: List[dict],
        origin: Tuple[float, float],
        max_distance_km: float = 30.0
    ) -> List[dict]:
        """Filter results to only nearby POIs within max_distance_km."""
        
        origin_lat, origin_lon = origin
        filtered = []
        
        for r in results:
            geom = r.get("geometry", {})
            coords = geom.get("coordinates", [])
            if not coords:
                continue
            
            res_lng, res_lat = coords[0], coords[1]
            dist = self._calculate_distance(origin_lat, origin_lon, res_lat, res_lng)
            
            if dist <= max_distance_km:
                r["_dist"] = dist
                r["_is_poi"] = r.get("properties", {}).get("feature_type") == "poi"
                filtered.append(r)
        
        # Sort: POIs first, then by distance
        filtered.sort(key=lambda x: (not x.get("_is_poi", False), x.get("_dist", float("inf"))))
        return filtered

    def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str = "driving"
    ) -> Optional[dict]:
        """Get route using Mapbox Directions API."""
        
        profile_map = {
            "driving": "mapbox/driving",
            "walking": "mapbox/walking",
            "bicycling": "mapbox/cycling",
        }
        profile = profile_map.get(mode, "mapbox/driving")
        
        coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        url = f"https://api.mapbox.com/directions/v5/{profile}/{coords}"
        params = {
            "access_token": self.token,
            "geometries": "polyline",
            "overview": "full",
            "steps": "true",
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if not data.get("routes"):
                return None
            
            route = data["routes"][0]
            leg = route["legs"][0]
            
            steps = []
            for s in leg.get("steps", []):
                maneuver = s.get("maneuver", {})
                banner = s.get("bannerInstructions", [])
                
                instruction = ""
                if banner:
                    instruction = banner[0].get("primary", {}).get("text", "")
                if not instruction:
                    maneuver_type = maneuver.get("type", "")
                    instruction = maneuver.get("instruction", "")
                    if not instruction and maneuver_type:
                        instruction = f"{maneuver_type.replace('_', ' ').title()}"
                
                steps.append({
                    "instruction": instruction,
                    "distance_text": s.get("distance", 0),
                    "type": maneuver.get("type", "")
                })
            
            # Handle polyline encoding
            polyline = route.get("geometry")
            if isinstance(polyline, dict):
                polyline = polyline.get("coordinates")
            if isinstance(polyline, list) and polyline:
                from utils.polyline import encode_polyline
                polyline = encode_polyline(polyline)
            
            deeplink = (
                f"https://www.mapbox.com/directions/?api=1"
                f"&origin={origin[0]},{origin[1]}"
                f"&destination={destination[0]},{destination[1]}"
                f"&mode={mode}"
            )
            
            return {
                "origin": {"lat": origin[0], "lng": origin[1]},
                "destination": {"lat": destination[0], "lng": destination[1]},
                "mode": mode,
                "distance_text": leg.get("distance", 0),
                "duration_text": leg.get("duration", 0),
                "polyline": polyline,
                "steps": steps,
                "maps_deeplink": deeplink,
            }
            
        except Exception as e:
            logger.error(f"Mapbox Directions error: {e}")
            return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """Reverse geocode coordinates to address."""
        
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
        params = {"access_token": self.token, "limit": 1}
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get("features"):
                return data["features"][0].get("place_name")
                
        except Exception as e:
            logger.error(f"Mapbox geocode error: {e}")
        
        return None

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate approximate distance in km using simple projection."""
        # Simple equirectangular approximation
        return math.sqrt(
            ((lon2 - lon1) * math.cos((lat1 + lat2) / 2 * math.pi / 180)) ** 2 +
            (lat2 - lat1) ** 2
        ) * 111  # rough km per degree


# Singleton instance
_mapbox_provider: Optional[MapboxProvider] = None


def get_mapbox_provider() -> MapboxProvider:
    global _mapbox_provider
    if _mapbox_provider is None:
        _mapbox_provider = MapboxProvider()
    return _mapbox_provider