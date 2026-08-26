"""Ranking service - scores and ranks search results."""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RankingService:
    """Scores and ranks place results based on multiple factors."""

    # Weights for scoring
    WEIGHTS = {
        "distance": 0.30,      # Closer is better
        "rating": 0.20,        # Higher rated is better
        "poi_match": 0.15,     # POI vs street address
        "text_match": 0.15,    # Name matches query
        "type_match": 0.10,    # Category matches
        "session_relevance": 0.10,  # Based on session context
    }

    def rank(
        self,
        places: List[dict],
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> List[dict]:
        """
        Rank places by multiple scoring factors.
        
        Args:
            places: List of place dictionaries
            query: Original user query
            filters: Optional filters (open_now, etc.)
            session_context: Optional session info for relevance scoring
            
        Returns:
            Sorted list of places with scores added
        """
        if not places:
            return []
        
        query_lower = query.lower()
        
        scored = []
        for place in places:
            score = self._calculate_score(
                place=place,
                query_lower=query_lower,
                filters=filters or {},
                session_context=session_context or {}
            )
            place["_rank_score"] = score
            scored.append(place)
        
        # Sort by score descending
        scored.sort(key=lambda x: x.get("_rank_score", 0), reverse=True)
        return scored

    def _calculate_score(
        self,
        place: dict,
        query_lower: str,
        filters: Dict[str, Any],
        session_context: Dict[str, Any]
    ) -> float:
        """Calculate composite score for a place."""
        
        score = 0.0
        
        # Distance score (0-1, smooth linear decay)
        dist = place.get("distance_km") or 999
        dist_score = max(0.0, 1.0 - (dist / 30.0))
        score += dist_score * self.WEIGHTS["distance"]
        
        # Rating score (0-1, higher is better)
        rating = place.get("rating")
        if rating is not None and rating > 0:
            rating_score = rating / 5.0
            score += rating_score * self.WEIGHTS["rating"]
        
        # POI vs Street score
        is_poi = place.get("poi_categories") and len(place.get("poi_categories", [])) > 0
        if is_poi:
            score += 1.0 * self.WEIGHTS["poi_match"]
        
        # Text match score
        name_lower = place.get("name", "").lower()
        if name_lower in query_lower:
            score += 1.0 * self.WEIGHTS["text_match"]
        elif any(w in name_lower for w in query_lower.split() if len(w) > 3):
            score += 0.5 * self.WEIGHTS["text_match"]
        
        # Type match (use real POI categories)
        type_keywords = {
            "cafe": ["cafe", "coffee", "espresso"],
            "restaurant": ["restaurant", "food", "dining"],
            "gas_station": ["gas_station", "fuel"],
            "pharmacy": ["pharmacy", "drugstore"],
            "hotel": ["hotel", "lodging"],
        }
        place_cats = [c.lower() for c in place.get("poi_categories", [])]
        for cat, keywords in type_keywords.items():
            if any(k in query_lower for k in keywords):
                if any(k in pc for pc in place_cats for k in keywords):
                    score += 0.5 * self.WEIGHTS["type_match"]
        
        # Session relevance (if user selected from previous results)
        if session_context.get("last_results"):
            last_names = [p.get("name", "").lower() for p in session_context["last_results"]]
            if place.get("name", "").lower() in last_names:
                score += 0.5 * self.WEIGHTS["session_relevance"]
        
        return score

    def select_by_index(
        self,
        places: List[dict],
        index: Optional[int]
    ) -> Optional[dict]:
        """Select a place by index (e.g., "the second one")."""
        if index is None or index < 0 or index >= len(places):
            return None
        return places[index]


# Singleton
_ranking_service: Optional[RankingService] = None


def get_ranking_service() -> RankingService:
    global _ranking_service
    if _ranking_service is None:
        _ranking_service = RankingService()
    return _ranking_service