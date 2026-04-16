"""Tests for intent extraction - mock-based to avoid API calls."""
import pytest
from unittest.mock import patch


class TestIntentFallback:
    """Test fallback intent detection without API calls."""

    @patch('providers.gemini_provider.get_gemini_key')
    def test_search_places_intent_fallback(self, mock_key):
        """Test fallback intent detection for search places."""
        mock_key.return_value = "fake_key"
        from providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider._fallback_intent("find coffee nearby")
        assert result["intent"] == "search_places"

    @patch('providers.gemini_provider.get_gemini_key')
    def test_route_intent_fallback(self, mock_key):
        """Test fallback intent detection for route."""
        mock_key.return_value = "fake_key"
        from providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider._fallback_intent("navigate me to starbucks")
        assert result["intent"] == "route"

    @patch('providers.gemini_provider.get_gemini_key')
    def test_where_am_i_intent_fallback(self, mock_key):
        """Test fallback intent detection for where am I."""
        mock_key.return_value = "fake_key"
        from providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider._fallback_intent("where am I")
        assert result["intent"] == "where_am_i"

    @patch('providers.gemini_provider.get_gemini_key')
    def test_search_terms_in_result(self, mock_key):
        """Test search terms are extracted in fallback."""
        mock_key.return_value = "fake_key"
        from providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider._fallback_intent("find quiet coffee shop")
        assert len(result["search_terms"]) > 0

    @patch('providers.gemini_provider.get_gemini_key')
    def test_follow_up_detection(self, mock_key):
        """Test follow-up flag in result."""
        mock_key.return_value = "fake_key"
        from providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = provider._fallback_intent("the second one")
        assert "selected_index" in result