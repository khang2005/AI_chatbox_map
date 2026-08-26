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

    async def handle(self, query: str, location: Optional[dict], mode: str, session_id: str) -> dict:
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
        session_context = self.memory.get_context(session_id)
        
        intent = await self.gemini.extract_intent(query, session_context)
        logger.info(f"Extracted intent: {intent}")
        
        if intent.get("intent") == "where_am_i":
            return self._handle_where_am_i(location, session_id, query)
        
        if not location:
            return self._error_response("no_location")
        
        origin = (location["lat"], location["lng"])
        
        is_replacement = self._looks_like_replacement_search(query, intent)
        
        if self._should_reuse_previous_results(query, intent, session_context):
            return await self._handle_follow_up(
                query, origin, intent, session_context, session_id, mode
            )
        
        if is_replacement:
            self.memory.upsert_session(
                session_id,
                current_route=None,
                search_context_updates={"last_category": self._extract_category(query)}
            )
        
        wants_route = self.route.is_route_intent(query)
        
        raw_results = self.place_search.search(
            query=query,
            origin=origin,
            intent_data=intent,
            max_results=5,
            max_distance_km=30.0
        )
        
        places = self.place_search.normalize_results(raw_results)
        
        if not places:
            self.memory.upsert_session(
                session_id,
                last_user_query=query,
                last_intent=intent,
                last_results=[],
                search_context_updates={"last_category": self._extract_category(query)}
            )
            return {
                "response": self.response.generate_error("no_results"),
                "places": [],
                "directions": []
            }
        
        ranked_places = self.ranking.rank(
            places=places,
            query=query,
            filters=intent.get("filters", {}),
            session_context=session_context
        )
        
        selected_index = intent.get("selected_index")
        if selected_index is not None:
            selected = self.ranking.select_by_index(ranked_places, selected_index)
            if selected:
                ranked_places = [selected]
        
        directions = []
        new_route = None
        
        if wants_route and ranked_places:
            dest = ranked_places[0]["location"]
            route_result = self.route.get_route(
                origin=origin,
                destination=(dest["lat"], dest["lng"]),
                mode=mode
            )
            if route_result:
                directions = [route_result]
                new_route = route_result
        
        response_text = await self.response.generate(
            user_query=query,
            places=ranked_places,
            directions=directions[0] if directions else None,
            intent=intent
        )
        
        self.memory.upsert_session(
            session_id,
            last_user_query=query,
            last_intent=intent,
            last_results=ranked_places,
            selected_place=ranked_places[0] if ranked_places else None,
            last_origin=location,
            current_route=new_route,
            search_context_updates={"last_category": self._extract_category(query)}
        )
        
        return {
            "response": response_text,
            "places": ranked_places,
            "directions": directions
        }

    def _should_reuse_previous_results(self, query: str, intent: dict, session_context: dict) -> bool:
        if not session_context.get("last_results"):
            return False

        if intent.get("follow_up_mode") == "select":
            return True

        if intent.get("selected_index") is not None:
            return True

        query_lower = query.lower().strip()

        explicit_reference_phrases = (
            "that one",
            "this one",
            "there",
            "the first",
            "the second",
            "the third",
            "navigate there",
            "take me there",
            "route there",
            "is it open",
            "is that open",
        )
        if any(phrase in query_lower for phrase in explicit_reference_phrases):
            return True

        if intent.get("follow_up_mode") == "refine":
            return True

        return False

    def _looks_like_replacement_search(self, query: str, intent: dict) -> bool:
        if intent.get("follow_up_mode") == "replace_search":
            return True

        query_lower = query.lower().strip()

        replacement_terms = (
            "market",
            "mall",
            "grocery",
            "supermarket",
            "gas station",
            "pharmacy",
            "restaurant",
            "cafe",
            "hotel",
            "bank",
            "hospital",
            "park",
        )

        replacement_phrases = (
            "how about",
            "what about",
            "instead",
            "i want",
            "show me a",
            "show me an",
            "find a",
            "find an",
        )

        has_replacement_phrase = any(p in query_lower for p in replacement_phrases)
        has_replacement_term = any(t in query_lower for t in replacement_terms)

        return has_replacement_phrase and has_replacement_term

    def _extract_category(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        categories = ["coffee", "cafe", "market", "mall", "restaurant", "gas station", 
                      "pharmacy", "hotel", "bank", "hospital", "park", "starbucks"]
        for cat in categories:
            if cat in query_lower:
                return cat
        return None

    def _handle_where_am_i(self, location: Optional[dict], session_id: str, query: str) -> dict:
        if not location:
            return self._error_response("no_location")
        
        address = self.mapbox.reverse_geocode(location["lat"], location["lng"])
        
        if address:
            response = self.response.generate_where_am_i(address)
        else:
            response = f"Your coordinates are: {location['lat']}, {location['lng']}"
        
        self.memory.upsert_session(
            session_id,
            last_user_query=query,
            last_intent={"intent": "where_am_i"},
            last_origin=location
        )
        
        return {
            "response": response,
            "places": [],
            "directions": []
        }

    async def _handle_follow_up(
        self,
        query: str,
        origin: Tuple[float, float],
        intent: dict,
        session_context: dict,
        session_id: str,
        mode: str
    ) -> dict:
        last_results = session_context.get("last_results", [])
        
        if intent.get("selected_index") is not None:
            selected = self.ranking.select_by_index(last_results, intent["selected_index"])
            
            if not selected:
                return self._error_response("no_results")
            
            wants_route = self.route.is_route_intent(query)
            directions = []
            new_route = None
            
            if wants_route:
                dest = selected["location"]
                route_result = self.route.get_route(
                    origin=origin,
                    destination=(dest["lat"], dest["lng"]),
                    mode=mode
                )
                if route_result:
                    directions = [route_result]
                    new_route = route_result
            
            response_text = await self.response.generate(
                user_query=query,
                places=[selected],
                directions=directions[0] if directions else None,
                intent={"intent": "follow_up", "sub_intent": intent.get("sub_intent")}
            )
            
            self.memory.upsert_session(
                session_id,
                last_user_query=query,
                selected_place=selected,
                current_route=new_route
            )
            
            return {
                "response": response_text,
                "places": [selected],
                "directions": directions
            }
        
        response_text = await self.response.generate_follow_up(
            query=query,
            context=session_context,
            is_result_reference=True
        )
        
        return {
            "response": response_text,
            "places": last_results[:3],
            "directions": [session_context.get("current_route")] if session_context.get("current_route") else []
        }

    def _error_response(self, error_type: str) -> dict:
        return {
            "response": self.response.generate_error(error_type),
            "places": [],
            "directions": []
        }


_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
