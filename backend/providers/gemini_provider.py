"""Gemini API provider for structured intent extraction."""
import json
import logging
from typing import Optional

import google.generativeai as genai

from utils.config import get_gemini_key

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Wrapper for Gemini API to return structured JSON responses."""

    def __init__(self):
        api_key = get_gemini_key()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def extract_intent(
        self,
        user_query: str,
        session_context: Optional[dict] = None
    ) -> dict:
        """Extract structured intent from user query using Gemini."""
        
        context_str = ""
        if session_context:
            context_str = f"""
Previous context:
- Last query: {session_context.get('last_query', 'N/A')}
- Last intent: {session_context.get('last_intent', 'N/A')}
- Last results: {session_context.get('last_results_count', 0)} places found
- Selected place: {session_context.get('selected_place', 'None')}
"""

        prompt = f"""You are an intent extraction system for a map assistant. 
Analyze the user's query and return a JSON object with the intent.

{context_str}

User query: {user_query}

Return a JSON object with these fields:
- intent: one of "search_places", "route", "where_am_i", "general_chat"
- sub_intent: optional modifier like "study_friendly", "cheap", "open_now"
- search_terms: array of search queries to try (expand the user query)
- filters: object with optional filters like open_now, distance_km
- follow_up_to_previous: boolean, true if this seems to follow up on previous results
- selected_index: integer, if user refers to "the second one", "that one", etc.

Example output:
{{
  "intent": "search_places",
  "sub_intent": "quiet",
  "search_terms": ["quiet coffee shop", "study cafe", "coffee with seating"],
  "filters": {{"open_now": false}},
  "follow_up_to_previous": false,
  "selected_index": null
}}

Return ONLY valid JSON, no explanations:"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Handle markdown-wrapped JSON
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text.strip())
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._fallback_intent(user_query)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_intent(user_query)

    def generate_response(
        self,
        user_query: str,
        places: list,
        directions: Optional[dict] = None,
        intent: Optional[dict] = None
    ) -> str:
        """Generate natural language response after search/ranking."""
        
        places_info = ""
        if places:
            places_info = "\n".join([
                f"- {p.get('name', 'Unknown')} at {p.get('location', {}).get('lat', 0)}, {p.get('location', {}).get('lng', 0)}"
                f" ({p.get('vicinity', 'No address')})"
                for p in places[:3]
            ])
        
        route_info = ""
        if directions:
            route_info = f"""
Route found:
- Distance: {directions.get('distance_text', 0)} meters
- Duration: {directions.get('duration_text', 0)} seconds
- Mode: {directions.get('mode', 'driving')}
"""
        
        prompt = f"""You are a helpful map assistant. Respond to the user's query about locations, places, or directions.

User query: {user_query}

Intent: {intent.get('intent') if intent else 'unknown'}

Found places:
{places_info if places_info else "No specific places found nearby."}

{route_info}

Keep responses concise, friendly, and mention the places found. If directions are available, mention them.
Response:"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini response generation error: {e}")
            return self._fallback_response(places, directions)

    def _fallback_intent(self, user_query: str) -> dict:
        """Fallback intent extraction when Gemini fails."""
        query_lower = user_query.lower()
        
        # Simple keyword-based fallback
        if any(w in query_lower for w in ["where am i", "my location", "current location"]):
            return {
                "intent": "where_am_i",
                "sub_intent": None,
                "search_terms": [],
                "filters": {},
                "follow_up_to_previous": False,
                "selected_index": None
            }
        
        if any(w in query_lower for w in ["get me to", "take me to", "navigate", "directions", "route to"]):
            return {
                "intent": "route",
                "sub_intent": None,
                "search_terms": [user_query],
                "filters": {},
                "follow_up_to_previous": False,
                "selected_index": None
            }
        
        return {
            "intent": "search_places",
            "sub_intent": None,
            "search_terms": [user_query],
            "filters": {},
            "follow_up_to_previous": False,
            "selected_index": None
        }

    def _fallback_response(self, places: list, directions: Optional[dict]) -> str:
        """Fallback response without AI."""
        if not places:
            return "Sorry, I couldn't find places for that query."
        
        names = ", ".join([str(p.get("name", "Unknown")) for p in places[:3]])
        if directions:
            return f"I found {names}. Route: {directions.get('distance_text', 0)}m, {directions.get('duration_text', 0)}s."
        return f"I found these nearby: {names}. Want directions?"


# Singleton instance
_gemini_provider: Optional[GeminiProvider] = None


def get_gemini_provider() -> GeminiProvider:
    global _gemini_provider
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
    return _gemini_provider