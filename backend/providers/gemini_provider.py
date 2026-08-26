"""Gemini API provider for structured intent extraction."""
import json
import logging
from typing import Optional
import asyncio

import google.generativeai as genai

from utils.config import get_gemini_key

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Wrapper for Gemini API to return structured JSON responses."""

    def __init__(self):
        api_key = get_gemini_key()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-flash-latest")
        self.max_retries = 3
        self.timeout = 15
        self.max_tokens = 1000

    async def extract_intent(
        self,
        user_query: str,
        session_context: Optional[dict] = None
    ) -> dict:
        """Extract structured intent from user query using Gemini with retry logic."""
        
        context_str = ""
        if session_context:
            selected_place = session_context.get("selected_place")
            selected_place_name = (
                selected_place.get("name")
                if isinstance(selected_place, dict)
                else "None"
            )
            
            last_results = session_context.get("last_results", [])
            last_results_count = len(last_results) if last_results else 0
            
            context_str = f"""
Previous context:
- Last query: {session_context.get('last_user_query', 'N/A')}
- Last intent: {session_context.get('last_intent', 'N/A')}
- Last results: {last_results_count} places found
- Selected place: {selected_place_name}
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
- follow_up_mode: one of "select", "refine", "replace_search", "none"
- selected_index: integer, if user refers to "the second one", "that one", etc.

follow_up_mode values:
- "select": User wants to select from previous results (e.g., "the second one", "that one")
- "refine": User wants to refine/filter previous results (e.g., "which is open now")
- "replace_search": User is doing a new/different search (e.g., "how about a market", "what about coffee")
- "none": No follow-up behavior, fresh search

Example outputs:
{{
  "intent": "search_places",
  "sub_intent": "quiet",
  "search_terms": ["quiet coffee shop", "study cafe", "coffee with seating"],
  "filters": {{"open_now": false}},
  "follow_up_to_previous": false,
  "follow_up_mode": "none",
  "selected_index": null
}}

{{
  "intent": "search_places",
  "sub_intent": null,
  "search_terms": ["market"],
  "filters": {{}},
  "follow_up_to_previous": true,
  "follow_up_mode": "replace_search",
  "selected_index": null
}}

Return ONLY valid JSON, no explanations:"""

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.model.generate_content, prompt),
                    timeout=self.timeout
                )
                text = response.text.strip()
                
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                result = json.loads(text.strip())
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Gemini timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return self._fallback_intent(user_query)
                await asyncio.sleep(2 ** attempt)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                if attempt == self.max_retries - 1:
                    return self._fallback_intent(user_query)
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return self._fallback_intent(user_query)
                await asyncio.sleep(2 ** attempt)
        
        return self._fallback_intent(user_query)

    async def generate_response(
        self,
        user_query: str,
        places: list,
        directions: Optional[dict] = None,
        intent: Optional[dict] = None
    ) -> str:
        """Generate natural language response after search/ranking with safety wrapper."""
        
        places_info = ""
        if places:
            parts = []
            for p in places[:3]:
                line = f"- {p.get('name', 'Unknown')}"
                dist = p.get("distance_km")
                if dist is not None:
                    line += f" — {dist:.1f} km away"
                rating = p.get("rating")
                if rating is not None:
                    line += f", rated {rating}/5"
                review_count = p.get("review_count")
                if review_count is not None:
                    line += f" ({review_count} reviews)"
                price = p.get("price")
                if price:
                    line += f", {price}"
                is_open = p.get("is_open")
                if is_open is True:
                    line += ", open now"
                elif is_open is False:
                    line += ", currently closed"
                address = p.get("vicinity", "")
                if address:
                    line += f"\n  Address: {address}"
                phone = p.get("phone")
                if phone:
                    line += f"\n  Phone: {phone}"
                website = p.get("website")
                if website:
                    line += f"\n  Website: {website}"
                cats = p.get("poi_categories", [])
                if cats:
                    line += f"\n  Categories: {', '.join(cats)}"
                parts.append(line)
            places_info = "\n".join(parts)
        
        route_info = ""
        if directions:
            route_info = f"""
Route found:
- Distance: {directions.get('distance_text', 0)} meters
- Duration: {directions.get('duration_text', 0)} seconds
- Mode: {directions.get('mode', 'driving')}
"""
        
        prompt = f"""You are a knowledgeable local guide. Respond to the user's query about places with detailed, helpful information.

User query: {user_query}

Intent: {intent.get('intent') if intent else 'unknown'}

Found places:
{places_info if places_info else "No specific places found nearby."}

{route_info}

Instructions:
- Be conversational and enthusiastic, like a local friend recommending spots
- Mention distances, ratings, and prices when available
- If places are found, briefly describe each one and what makes it notable
- Compare options when multiple results exist (e.g., "Starbucks is closer, but Peet's has better reviews")
- If a route is available, mention the travel time and distance
- If no places found, suggest broadening the search
- Keep responses detailed but not overwhelming (2-4 sentences per place)
Response:"""

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.model.generate_content, prompt),
                    timeout=self.timeout
                )
                return response.text
                
            except asyncio.TimeoutError:
                logger.warning(f"Gemini response timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return self._fallback_response(places, directions)
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Gemini response generation error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return self._fallback_response(places, directions)
                await asyncio.sleep(2 ** attempt)
        
        return self._fallback_response(places, directions)

    def _fallback_intent(self, user_query: str) -> dict:
        """Fallback intent extraction when Gemini fails."""
        query_lower = user_query.lower()
        
        if any(w in query_lower for w in ["where am i", "my location", "current location"]):
            return {
                "intent": "where_am_i",
                "sub_intent": None,
                "search_terms": [],
                "filters": {},
                "follow_up_to_previous": False,
                "follow_up_mode": "none",
                "selected_index": None
            }
        
        if any(w in query_lower for w in ["get me to", "take me to", "navigate", "directions", "route to"]):
            return {
                "intent": "route",
                "sub_intent": None,
                "search_terms": [user_query],
                "filters": {},
                "follow_up_to_previous": False,
                "follow_up_mode": "none",
                "selected_index": None
            }
        
        return {
            "intent": "search_places",
            "sub_intent": None,
            "search_terms": [user_query],
            "filters": {},
            "follow_up_to_previous": False,
            "follow_up_mode": "none",
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


_gemini_provider: Optional[GeminiProvider] = None


def get_gemini_provider() -> GeminiProvider:
    global _gemini_provider
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
    return _gemini_provider
