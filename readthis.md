You are refactoring the backend of the AI_chatbox_map project.

Goal:
Fix stale follow up behavior and implement proper conversational memory for nearby place search and navigation.

Important behavior to support:
1. "get me to a nearby starbucks"
2. "how about a market"
3. "no i want to go to a mall"
4. "the second one"
5. "navigate there"
6. "is it open now"

Current bug:
The system reuses old Starbucks results when the user changes category. New category searches are being treated like follow ups to previous results. Memory is also too weak and not structured enough.

Requirements:
1. Do not use MySQL for conversational memory.
2. Implement structured session memory in MemoryService.
3. Use in memory storage with optional JSON file persistence for development.
4. Design the code so Redis can be added later without changing orchestrator behavior.
5. Keep route handlers thin.
6. Keep business logic in services.
7. Use type hints and PEP 8 style.

Implement the following changes.

File 1: backend/schemas/session.py
Create a new file with Pydantic models for conversational memory.

Use this code:

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionSearchContext(BaseModel):
    last_category: Optional[str] = None
    last_area_name: Optional[str] = None
    last_action: Optional[str] = None


class SessionMemory(BaseModel):
    session_id: str
    last_user_query: Optional[str] = None
    last_intent: Dict[str, Any] = Field(default_factory=dict)
    last_results: List[Dict[str, Any]] = Field(default_factory=list)
    selected_place: Optional[Dict[str, Any]] = None
    current_route: Optional[Dict[str, Any]] = None
    last_origin: Optional[Dict[str, float]] = None
    search_context: SessionSearchContext = Field(default_factory=SessionSearchContext)
    updated_at: float = 0.0


File 2: backend/services/memory_service.py
Refactor MemoryService to store structured session memory.
Add optional JSON persistence.
Do not depend on MySQL.

Use this code:

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from schemas.session import SessionMemory


class MemoryService:
    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._store: Dict[str, SessionMemory] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path:
            self._load()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        session = self._store.get(session_id)
        if not session:
            session = SessionMemory(session_id=session_id, updated_at=time.time())
            self._store[session_id] = session
            self._save()
        return session.model_dump()

    def upsert_session(
        self,
        session_id: str,
        *,
        last_user_query: Optional[str] = None,
        last_intent: Optional[Dict[str, Any]] = None,
        last_results: Optional[list[Dict[str, Any]]] = None,
        selected_place: Optional[Dict[str, Any]] = None,
        current_route: Optional[Dict[str, Any]] = None,
        last_origin: Optional[Dict[str, float]] = None,
        search_context_updates: Optional[Dict[str, Any]] = None,
        clear_route: bool = False,
    ) -> Dict[str, Any]:
        raw = self.get_session(session_id)
        session = SessionMemory(**raw)

        if last_user_query is not None:
            session.last_user_query = last_user_query
        if last_intent is not None:
            session.last_intent = last_intent
        if last_results is not None:
            session.last_results = last_results
        if selected_place is not None:
            session.selected_place = selected_place
        if current_route is not None:
            session.current_route = current_route
        if clear_route:
            session.current_route = None
        if last_origin is not None:
            session.last_origin = last_origin

        if search_context_updates:
            ctx = session.search_context.model_dump()
            ctx.update(search_context_updates)
            session.search_context = session.search_context.__class__(**ctx)

        session.updated_at = time.time()
        self._store[session_id] = session
        self._save()
        return session.model_dump()

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        data = json.loads(self._persist_path.read_text(encoding="utf-8"))
        for session_id, payload in data.items():
            self._store[session_id] = SessionMemory(**payload)

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            session_id: session.model_dump()
            for session_id, session in self._store.items()
        }
        self._persist_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


File 3: backend/providers/gemini_provider.py
Fix the prompt context so it uses real session values.
Do not reference last_results_count unless it actually exists.

Find code that formats session context and replace it with logic like this:

selected_place = session_context.get("selected_place")
selected_place_name = (
    selected_place.get("name")
    if isinstance(selected_place, dict)
    else "None"
)

last_results_count = len(session_context.get("last_results", []))

Then use:
- Last results: {last_results_count} places found
- Selected place: {selected_place_name}

Also extend intent output schema to support:
follow_up_mode with allowed values:
- select
- refine
- replace_search
- none

If Gemini output is missing or invalid, default safely.

File 4: backend/services/intent_service.py
Create a dedicated intent service instead of mixing domain logic into gemini_provider.py.

Use this code:

from __future__ import annotations

from typing import Any, Dict

from providers.gemini_provider import GeminiProvider


class IntentService:
    def __init__(self, gemini_provider: GeminiProvider) -> None:
        self.gemini_provider = gemini_provider

    def extract_intent(self, query: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        intent = self.gemini_provider.extract_intent(query, session_context)

        if "follow_up_to_previous" not in intent:
            intent["follow_up_to_previous"] = False

        if "follow_up_mode" not in intent:
            intent["follow_up_mode"] = "none"

        if "selected_index" not in intent:
            intent["selected_index"] = None

        return intent


File 5: backend/services/orchestrator.py
Refactor the follow up logic.

Requirements:
1. Only reuse previous results when the query clearly references previous results.
2. Treat category switches like market, mall, gas station, pharmacy, restaurant as replacement searches.
3. Fresh replacement searches must run a new search.
4. Clear old route when replacement search happens and no new route is generated.

Add these helper methods:

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


Then update main handle flow to do this:

1. Load session context
2. Extract intent
3. If _should_reuse_previous_results returns true, use _handle_follow_up
4. Otherwise run a fresh query rewrite and search flow
5. If _looks_like_replacement_search returns true, do not reuse last_results as answer source
6. Update memory with new results
7. Clear stale current_route when replacement search happens and no new route is returned

Update follow up handling so only true result references use old results.
If selected_index is present, select that place from last_results.
If query is a refinement like open now, pass last_results to response generation.
Do not let replacement searches enter this branch.

File 6: backend/services/response_service.py
Split follow up response generation into two modes:
1. true follow up on existing results
2. fresh search response

Do not use previous results inside generate_follow_up unless orchestrator has already decided the query is a true result reference.

If generate_follow_up currently always does:
places=context.get("last_results", [])[:3]
keep that behavior only for real result reference mode.

File 7: backend/schemas/chat.py
If place and route models are still mixed into chat schema, split them into:
backend/schemas/places.py
backend/schemas/session.py

Keep chat request and response models in chat.py only.

File 8: backend/main.py and dependency wiring
Wire in IntentService.
Instantiate MemoryService with optional JSON persistence path such as:
data/session_memory.json

Example:
memory_service = MemoryService(persist_path="data/session_memory.json")

File 9: tests
Add tests for these cases:

Test 1
Query: "get me to a nearby starbucks"
Expect:
fresh search
results stored
route may exist

Test 2
Next query: "how about a market"
Expect:
fresh search
results are not Starbucks
old last_results replaced
old route cleared unless new route generated

Test 3
Next query: "no i want to go to a mall"
Expect:
fresh search for mall
no Starbucks leakage

Test 4
After a search with multiple results
Query: "the second one"
Expect:
selected place equals index 1 from prior results

Test 5
Query: "navigate there"
Expect:
route generated for selected place or best prior selected result

Test 6
Memory persistence
Restart MemoryService with same JSON path
Expect:
session reloads correctly

Implementation notes:
1. Keep providers thin.
2. Keep domain decisions in services.
3. Use type hints everywhere.
4. Do not introduce MySQL for this memory layer.
5. Design MemoryService so a future RedisMemoryService can implement the same interface.

Success criteria:
1. New category searches no longer reply with stale Starbucks results.
2. "the second one" still works.
3. Session memory survives restarts in development when JSON persistence is enabled.
4. Orchestrator clearly separates result reference follow ups from replacement searches.
