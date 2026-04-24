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
        self._max_history_messages = 5
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
            # Trim and validate user query
            last_user_query = last_user_query.strip()[:500]  # Max 500 chars
            if last_user_query:
                session.last_user_query = last_user_query

        if last_intent is not None:
            session.last_intent = last_intent

        if last_results is not None:
            # Limit results to prevent excessive memory usage
            session.last_results = last_results[:10]  # Max 10 results

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

    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get trimmed context for LLM calls with token control."""
        session_data = self.get_session(session_id)
        session = SessionMemory(**session_data)
        
        # Use the built-in method to get trimmed context
        return session.trim_context_for_llm()

    def get_conversation_history(self, session_id: str, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history with token control."""
        session_data = self.get_session(session_id)
        session = SessionMemory(**session_data)
        
        max_limit = max_messages or self._max_history_messages
        return session.get_conversation_history(max_limit)

    def clear_session(self, session_id: str) -> None:
        if session_id in self._store:
            del self._store[session_id]
            self._save()

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


_memory_service: Optional[MemoryService] = None


def get_memory_service(persist_path: Optional[str] = None) -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService(persist_path=persist_path)
    return _memory_service
