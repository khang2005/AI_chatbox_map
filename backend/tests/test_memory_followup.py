"""Tests for memory service and follow-up behavior."""
import pytest
import tempfile
import time
from pathlib import Path

from services.memory_service import MemoryService


class TestMemoryService:
    """Test MemoryService with JSON persistence."""

    def test_get_session_creates_new(self):
        """Test that get_session creates a new session if none exists."""
        service = MemoryService()
        session = service.get_session("test-session-1")
        
        assert session["session_id"] == "test-session-1"
        assert session["last_results"] == []
        assert session["selected_place"] is None

    def test_upsert_session_updates(self):
        """Test that upsert_session updates session fields."""
        service = MemoryService()
        
        service.upsert_session(
            "test-session-2",
            last_user_query="coffee nearby",
            last_results=[{"name": "Starbucks", "location": {"lat": 1, "lng": 2}}],
        )
        
        session = service.get_session("test-session-2")
        assert session["last_user_query"] == "coffee nearby"
        assert len(session["last_results"]) == 1
        assert session["last_results"][0]["name"] == "Starbucks"

    def test_upsert_session_clear_route(self):
        """Test clearing route with clear_route flag."""
        service = MemoryService()
        
        service.upsert_session(
            "test-session-3",
            current_route={"origin": {"lat": 1, "lng": 2}, "destination": {"lat": 3, "lng": 4}}
        )
        
        session = service.get_session("test-session-3")
        assert session["current_route"] is not None
        
        service.upsert_session("test-session-3", clear_route=True)
        session = service.get_session("test-session-3")
        assert session["current_route"] is None

    def test_search_context_updates(self):
        """Test updating search context."""
        service = MemoryService()
        
        service.upsert_session(
            "test-session-4",
            search_context_updates={"last_category": "coffee"}
        )
        
        session = service.get_session("test-session-4")
        assert session["search_context"]["last_category"] == "coffee"

    def test_json_persistence(self):
        """Test that sessions persist to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_path = Path(tmpdir) / "sessions.json"
            service1 = MemoryService(persist_path=str(persist_path))
            
            service1.upsert_session(
                "persist-test",
                last_user_query="test query",
                last_results=[{"name": "Test Place"}]
            )
            
            service2 = MemoryService(persist_path=str(persist_path))
            session = service2.get_session("persist-test")
            
            assert session["last_user_query"] == "test query"
            assert session["last_results"][0]["name"] == "Test Place"

    def test_clear_session(self):
        """Test clearing a session."""
        service = MemoryService()
        
        service.upsert_session("to-clear", last_user_query="test")
        assert service.get_session("to-clear")["last_user_query"] == "test"
        
        service.clear_session("to-clear")
        session = service.get_session("to-clear")
        assert session["last_user_query"] is None


class TestFollowUpLogic:
    """Test orchestrator follow-up detection logic."""

    def test_should_reuse_previous_results_select_mode(self):
        """Test that select mode triggers result reuse."""
        from services.orchestrator import Orchestrator
        from unittest.mock import MagicMock
        
        orch = Orchestrator.__new__(Orchestrator)
        
        session_context = {"last_results": [{"name": "Place 1"}, {"name": "Place 2"}]}
        intent = {"follow_up_mode": "select"}
        
        assert orch._should_reuse_previous_results("the second one", intent, session_context) is True

    def test_should_reuse_previous_results_selected_index(self):
        """Test that selected_index triggers result reuse."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        session_context = {"last_results": [{"name": "Place 1"}, {"name": "Place 2"}]}
        intent = {"selected_index": 1}
        
        assert orch._should_reuse_previous_results("show me that", intent, session_context) is True

    def test_should_reuse_previous_results_explicit_phrases(self):
        """Test explicit reference phrases trigger result reuse."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        session_context = {"last_results": [{"name": "Place 1"}, {"name": "Place 2"}]}
        intent = {"follow_up_mode": "none", "selected_index": None}
        
        phrases = ["that one", "this one", "the first", "the second", 
                   "navigate there", "take me there", "is it open"]
        
        for phrase in phrases:
            assert orch._should_reuse_previous_results(phrase, intent, session_context) is True

    def test_should_reuse_previous_results_no_results(self):
        """Test that empty results returns False."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        session_context = {"last_results": []}
        intent = {"follow_up_mode": "select"}
        
        assert orch._should_reuse_previous_results("the second one", intent, session_context) is False

    def test_replacement_search_market(self):
        """Test market query is detected as replacement search."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        intent = {"follow_up_mode": "none"}
        
        assert orch._looks_like_replacement_search("how about a market", intent) is True
        assert orch._looks_like_replacement_search("what about a mall", intent) is True
        assert orch._looks_like_replacement_search("i want a pharmacy", intent) is True

    def test_replacement_search_not_triggered_by_single_term(self):
        """Test that single replacement term without phrase is not a replacement."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        intent = {"follow_up_mode": "none"}
        
        assert orch._looks_like_replacement_search("market nearby", intent) is False
        assert orch._looks_like_replacement_search("find coffee", intent) is False

    def test_extract_category(self):
        """Test category extraction from query."""
        from services.orchestrator import Orchestrator
        
        orch = Orchestrator.__new__(Orchestrator)
        
        assert orch._extract_category("starbucks nearby") == "starbucks"
        assert orch._extract_category("how about a coffee shop") == "coffee"
        assert orch._extract_category("find a restaurant") == "restaurant"
        assert orch._extract_category("random query") is None


class TestIntentService:
    """Test IntentService defaults."""

    def test_extract_intent_adds_defaults(self):
        """Test that IntentService adds default values."""
        from services.intent_service import IntentService
        from unittest.mock import MagicMock
        
        mock_gemini = MagicMock()
        mock_gemini.extract_intent.return_value = {"intent": "search_places"}
        
        service = IntentService(mock_gemini)
        result = service.extract_intent("test query", {})
        
        assert result["follow_up_to_previous"] is False
        assert result["follow_up_mode"] == "none"
        assert result["selected_index"] is None
