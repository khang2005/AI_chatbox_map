"""Orchestrator - coordinates the full request handling pipeline."""
import logging
from typing import Optional, Tuple

from providers.gemini_provider import get_gemini_provider
from providers.mapbox_provider import get_mapbox_provider
from services.place_search_service import get_place_search_service
from services.ranking_service import get_ranking_service
from services.route_service import get_route_service
from services.memory_service import get_memory_service
from services.response_service import get_response_service

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the full request handling pipeline:
    
    User Query -> Intent Extraction -> Query Rewriting -> 
    Place Search -> Ranking -> Route (if needed) -> Response
    """

    def __init__(self):
        self.gemini = get_gemini_provider()
        self.mapbox = get_mapbox_provider()
        self.place_search = get_place_search_service()
        self.ranking = get_ranking_service()
        self.route = get_route_service()
        self.memory = get_memory_service()
        self.response = get_response_service()

    def handle(self, query: str, location: Optional[dict], mode: str, session_id: str) -> dict:
        """
        Handle a complete chat request.
        
        Args:
            query: User's text query
            location: Optional {lat, lng} dict
            mode: Travel mode (driving, walking, bicycling)
            session_id: Session identifier
            
        Returns:
            Response dict with response, places, directions
        """
        # Get session context for follow-up handling
        session_context = self.memory.get_context(session_id)
        
        # Step 1: Extract structured intent
        intent = self.gemini.extract_intent(query, session_context)
        logger.info(f"Extracted intent: {intent}")
        
        # Handle special intents first
        if intent.get("intent") == "where_am_i":
            return self._handle_where_am_i(location, session_id)
        
        if not location:
            return self._error_response("no_location")
        
        origin = (location["lat"], location["lng"])
        
        # Handle follow-up queries
        if intent.get("follow_up_to_previous") or self._is_follow_up(query, session_context):
            return self._handle_follow_up(
                query, origin, intent, session_context, session_id
            )
        
        # Step 2: Check if route intent
        wants_route = self.route.is_route_intent(query)
        
        # Step 3: Search for places
        raw_results = self.place_search.search(
            query=query,
            origin=origin,
            intent_data=intent,
            max_results=5,
            max_distance_km=30.0
        )
        
        places = self.place_search.normalize_results(raw_results)
        
        if not places:
            # Update memory and return error
            self.memory.update(
                session_id,
                last_query=query,
                last_intent=intent,
                last_results=[]
            )
            return {
                "response": self.response.generate_error("no_results"),
                "places": [],
                "directions": []
            }
        
        # Step 4: Rank results
        ranked_places = self.ranking.rank(
            places=places,
            query=query,
            filters=intent.get("filters", {}),
            session_context=session_context
        )
        
        # Handle selection by index ("the second one")
        selected_index = intent.get("selected_index")
        if selected_index is not None:
            selected = self.ranking.select_by_index(ranked_places, selected_index)
            if selected:
                ranked_places = [selected]
        
        directions = []
        
        # Step 5: Get route if needed
        if wants_route and ranked_places:
            dest = ranked_places[0]["location"]
            route_result = self.route.get_route(
                origin=origin,
                destination=(dest["lat"], dest["lng"]),
                mode=mode
            )
            if route_result:
                directions = [route_result]
        
        # Step 6: Generate response
        response_text = self.response.generate(
            user_query=query,
            places=ranked_places,
            directions=directions[0] if directions else None,
            intent=intent
        )
        
        # Update memory
        self.memory.update(
            session_id,
            last_query=query,
            last_intent=intent,
            last_results=ranked_places,
            selected_place=ranked_places[0] if ranked_places else None,
            current_map_center=location,
            current_route=directions[0] if directions else None
        )
        
        return {
            "response": response_text,
            "places": ranked_places,
            "directions": directions
        }

    def _handle_where_am_i(self, location: Optional[dict], session_id: str) -> dict:
        """Handle 'where am I' query."""
        if not location:
            return self._error_response("no_location")
        
        address = self.mapbox.reverse_geocode(location["lat"], location["lng"])
        
        if address:
            response = self.response.generate_where_am_i(address)
        else:
            response = f"Your coordinates are: {location['lat']}, {location['lng']}"
        
        self.memory.update(
            session_id,
            last_query="where am i",
            last_intent={"intent": "where_am_i"},
            current_map_center=location
        )
        
        return {
            "response": response,
            "places": [],
            "directions": []
        }

    def _handle_follow_up(
        self,
        query: str,
        origin: Tuple[float, float],
        intent: dict,
        session_context: dict,
        session_id: str
    ) -> dict:
        """Handle follow-up queries like 'show me the second one' or 'which is open now'."""
        
        # If selecting from previous results
        if intent.get("selected_index") is not None:
            last_results = session_context.get("last_results", [])
            selected = self.ranking.select_by_index(last_results, intent["selected_index"])
            
            if not selected:
                return self._error_response("no_results")
            
            wants_route = self.route.is_route_intent(query)
            directions = []
            
            if wants_route:
                dest = selected["location"]
                route_result = self.route.get_route(
                    origin=origin,
                    destination=(dest["lat"], dest["lng"]),
                    mode="driving"
                )
                if route_result:
                    directions = [route_result]
            
            response_text = self.response.generate(
                user_query=query,
                places=[selected],
                directions=directions[0] if directions else None,
                intent={"intent": "follow_up", "sub_intent": intent.get("sub_intent")}
            )
            
            self.memory.update(
                session_id,
                last_query=query,
                last_intent=intent,
                selected_place=selected,
                current_route=directions[0] if directions else None
            )
            
            return {
                "response": response_text,
                "places": [selected],
                "directions": directions
            }
        
        # Otherwise generate follow-up response
        response_text = self.response.generate_follow_up(query, session_context)
        
        return {
            "response": response_text,
            "places": session_context.get("last_results", []),
            "directions": [session_context.get("current_route")] if session_context.get("current_route") else []
        }

    def _is_follow_up(self, query: str, session_context: dict) -> bool:
        """Check if query is a follow-up to previous results."""
        query_lower = query.lower()
        follow_indicators = ["that one", "the first", "the second", "the third", 
                            "show me", "which one", "what about", "another"]
        return any(ind in query_lower for ind in follow_indicators) and session_context.get("last_results")

    def _error_response(self, error_type: str) -> dict:
        """Generate error response."""
        return {
            "response": self.response.generate_error(error_type),
            "places": [],
            "directions": []
        }


# Singleton
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator