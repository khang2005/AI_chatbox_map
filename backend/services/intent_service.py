from __future__ import annotations

import logging
from typing import Any, Dict
from functools import lru_cache

from providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class IntentService:
    def __init__(self, gemini_provider: GeminiProvider) -> None:
        self.gemini_provider = gemini_provider

    @lru_cache(maxsize=100)
    def extract_intent_cached(self, query: str, session_context_json: str) -> Dict[str, Any]:
        """Extract intent with caching to avoid duplicate Gemini calls."""
        session_context = eval(session_context_json) if session_context_json else {}
        return self._extract_intent_internal(query, session_context)

    async def extract_intent(self, query: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract intent using Gemini with fallback to rule-based detection."""
        try:
            # Try to use cached result first
            session_context_json = str(session_context) if session_context else ""
            try:
                return self.extract_intent_cached(query, session_context_json)
            except:
                # Cache miss or error, proceed with normal extraction
                pass
            
            # Try Gemini first
            intent = await self.gemini_provider.extract_intent(query, session_context)
            
        except Exception as e:
            logger.error(f"Gemini intent extraction failed: {e}")
            # Fallback to rule-based intent detection
            intent = self._fallback_intent(query)
        
        return self._normalize_intent(intent)

    def _extract_intent_internal(self, query: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method for Gemini intent extraction."""
        import asyncio
        return asyncio.run(self.gemini_provider.extract_intent(query, session_context))

    def _normalize_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize intent structure."""
        if "follow_up_to_previous" not in intent:
            intent["follow_up_to_previous"] = False

        if "follow_up_mode" not in intent:
            intent["follow_up_mode"] = "none"

        if "selected_index" not in intent:
            intent["selected_index"] = None

        return intent

    def _fallback_intent(self, user_query: str) -> Dict[str, Any]:
        """Rule-based intent detection when Gemini fails."""
        query_lower = user_query.lower().strip()
        
        # Check for location queries
        if any(phrase in query_lower for phrase in ["where am i", "my location", "current location"]):
            return {
                "intent": "where_am_i",
                "sub_intent": None,
                "search_terms": [],
                "filters": {},
                "follow_up_to_previous": False,
                "follow_up_mode": "none",
                "selected_index": None
            }
        
        # Check for routing queries
        route_keywords = [
            "get me to", "take me to", "navigate", "directions", "route to",
            "how to get to", "show me the way", "go to"
        ]
        if any(phrase in query_lower for phrase in route_keywords):
            return {
                "intent": "route",
                "sub_intent": None,
                "search_terms": [user_query],
                "filters": {},
                "follow_up_to_previous": False,
                "follow_up_mode": "none",
                "selected_index": None
            }
        
        # Check for search queries with common patterns
        search_keywords = [
            "find", "search", "looking for", "nearby", "around", "close to",
            "coffee", "food", "restaurant", "cafe", "shop", "store", "market",
            "mall", "bank", "atm", "gas", "hospital", "pharmacy"
        ]
        
        if any(keyword in query_lower for keyword in search_keywords):
            # Extract search terms
            search_terms = [user_query]
            
            # Expand common queries
            if "coffee" in query_lower:
                search_terms = ["coffee shop", "cafe", "coffee"]
            elif "food" in query_lower or "restaurant" in query_lower:
                search_terms = ["restaurant", "food", "place to eat"]
            elif "gas" in query_lower:
                search_terms = ["gas station", "petrol"]
            
            return {
                "intent": "search_places",
                "sub_intent": None,
                "search_terms": search_terms,
                "filters": {},
                "follow_up_to_previous": False,
                "follow_up_mode": "none",
                "selected_index": None
            }
        
        # Default to general chat
        return {
            "intent": "general_chat",
            "sub_intent": None,
            "search_terms": [],
            "filters": {},
            "follow_up_to_previous": False,
            "follow_up_mode": "none",
            "selected_index": None
        }
