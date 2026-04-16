"""Route service - handles navigation and directions."""
import logging
from typing import Optional, Tuple

from providers.mapbox_provider import get_mapbox_provider

logger = logging.getLogger(__name__)


class RouteService:
    """Service for calculating routes and directions."""

    def __init__(self):
        self.mapbox = get_mapbox_provider()

    def get_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str = "driving"
    ) -> Optional[dict]:
        """
        Calculate route between two points.
        
        Args:
            origin: (lat, lng) tuple
            destination: (lat, lng) tuple
            mode: "driving", "walking", or "bicycling"
            
        Returns:
            Route dictionary or None
        """
        return self.mapbox.get_directions(origin, destination, mode)

    def is_route_intent(self, query: str) -> bool:
        """Check if query is asking for directions."""
        query_lower = query.lower()
        route_words = (
            "get me to", "take me to", "route to", "directions to", "navigate to",
            "drive to", "walk to", "bike to", "how to get", "how do i get",
            "give me directions", "show me the way", "navigate", "directions"
        )
        
        for phrase in route_words:
            if phrase in query_lower:
                return True
        
        # Also check single words
        single_words = ("take", "get", "navigate", "drive", "walk", "bike", "route")
        for word in single_words:
            if f" {word} " in f" {query_lower} " or query_lower.startswith(word):
                return True
        
        return False


# Singleton
_route_service: Optional[RouteService] = None


def get_route_service() -> RouteService:
    global _route_service
    if _route_service is None:
        _route_service = RouteService()
    return _route_service