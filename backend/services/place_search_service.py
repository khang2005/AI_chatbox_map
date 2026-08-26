"""Place search service - orchestrates multiple search providers."""
import logging
from typing import List, Optional, Tuple

from providers.mapbox_provider import get_mapbox_provider
from services.query_rewriter import get_query_rewriter

logger = logging.getLogger(__name__)


class PlaceSearchService:
    """Service for searching places with multiple query expansion and fallback."""

    def __init__(self):
        self.mapbox = get_mapbox_provider()
        self.rewriter = get_query_rewriter()

    def search(
        self,
        query: str,
        origin: Tuple[float, float],
        intent_data: Optional[dict] = None,
        max_results: int = 5,
        max_distance_km: float = 30.0
    ) -> List[dict]:
        """
        Search for places with query expansion and filtering.
        
        Args:
            query: User query
            origin: (lat, lng) tuple
            intent_data: Optional structured intent from Gemini
            max_results: Maximum results to return
            max_distance_km: Maximum distance filter
            
        Returns:
            List of place dictionaries
        """
        # Get search queries (possibly expanded)
        search_queries = self.rewriter.rewrite(query, intent_data)
        
        all_results = []
        
        for sq in search_queries:
            results = self.mapbox.search_places(sq, origin, limit=10)
            
            if not results:
                continue
            
            # Filter to nearby
            filtered = self.mapbox.filter_nearby(results, origin, max_distance_km)
            
            for r in filtered:
                # Avoid duplicates by checking place_id or name+coords
                existing_ids = {p.get("_source_id") for p in all_results}
                source_id = r.get("properties", {}).get("mapbox_id") or r.get("id")
                
                if source_id not in existing_ids:
                    r["_source_id"] = source_id
                    all_results.append(r)
            
            # Stop if we have enough
            if len(all_results) >= max_results:
                break
        
        # Sort and limit
        all_results.sort(key=lambda x: (not x.get("_is_poi", False), x.get("_dist", float("inf"))))
        return all_results[:max_results]

    def normalize_results(self, raw_results: List[dict]) -> List[dict]:
        """Convert raw provider results to standardized format."""
        normalized = []
        
        for r in raw_results:
            props = r.get("properties", {})
            geom = r.get("geometry", {})
            coords = geom.get("coordinates", [])
            
            if not coords or len(coords) != 2:
                continue
            
            lng, lat = coords[0], coords[1]
            
            metadata = props.get("metadata", {})
            poi_categories = props.get("poi_category") or []
            brand_list = props.get("brand") or []

            place = {
                "name": props.get("name") or r.get("text") or "Unknown Place",
                "place_id": props.get("mapbox_id") or r.get("id"),
                "vicinity": props.get("full_address") or props.get("address") or r.get("place_name", ""),
                "location": {"lat": lat, "lng": lng},
                "rating": metadata.get("rating"),
                "review_count": metadata.get("review_count"),
                "phone": metadata.get("phone"),
                "website": metadata.get("website"),
                "price": metadata.get("price"),
                "is_open": props.get("operational_status") == "active",
                "brand": brand_list[0] if brand_list else None,
                "poi_categories": poi_categories,
                "types": [props.get("feature_type")] if props.get("feature_type") else [r.get("type")],
                "source": "mapbox",
                "distance_km": r.get("_dist") or (props.get("distance", 0) / 1000),
                "maps_deeplink": f"https://www.mapbox.com/search/?api=1&query={lat},{lng}"
            }
            normalized.append(place)
        
        return normalized


# Singleton
_place_search_service: Optional[PlaceSearchService] = None


def get_place_search_service() -> PlaceSearchService:
    global _place_search_service
    if _place_search_service is None:
        _place_search_service = PlaceSearchService()
    return _place_search_service