"""Tests for place search service - mock-based."""
import pytest
from unittest.mock import patch, MagicMock


class TestPlaceSearchService:
    """Test place search functionality."""

    @patch('services.place_search_service.get_mapbox_provider')
    def test_normalize_results_basic(self, mock_provider):
        """Test result normalization."""
        # Setup mock
        mock_mapbox = MagicMock()
        mock_provider.return_value = mock_mapbox
        
        from services.place_search_service import PlaceSearchService
        service = PlaceSearchService()
        
        raw = [
            {
                "properties": {"name": "Starbucks", "mapbox_id": "test123", "feature_type": "poi", "full_address": "123 Main St"},
                "geometry": {"coordinates": [-117.689, 34.083]},
                "type": "poi"
            }
        ]
        
        results = service.normalize_results(raw)
        
        assert len(results) == 1
        assert results[0]["name"] == "Starbucks"
        assert results[0]["location"]["lat"] == 34.083

    @patch('services.place_search_service.get_mapbox_provider')
    def test_normalize_filters_invalid(self, mock_provider):
        """Test invalid coordinates are filtered."""
        mock_mapbox = MagicMock()
        mock_provider.return_value = mock_mapbox
        
        from services.place_search_service import PlaceSearchService
        service = PlaceSearchService()
        
        raw = [
            {
                "properties": {"name": "Test"},
                "geometry": {"coordinates": []},
                "type": "poi"
            }
        ]
        
        results = service.normalize_results(raw)
        assert len(results) == 0


class TestRankingService:
    """Test ranking functionality."""

    def test_ranking_calculates_scores(self):
        """Test ranking adds scores to places."""
        from services.ranking_service import RankingService
        service = RankingService()
        
        places = [
            {"name": "Starbucks", "distance_km": 1.0, "types": ["poi"]},
            {"name": "Main St", "distance_km": 5.0, "types": ["Feature"]},
        ]
        
        ranked = service.rank(places, "starbucks coffee")
        
        assert all("_rank_score" in p for p in ranked)
        # POI should rank higher than street
        assert ranked[0]["_rank_score"] >= ranked[1]["_rank_score"]

    def test_select_by_index(self):
        """Test selection by index."""
        from services.ranking_service import RankingService
        service = RankingService()
        
        places = [{"name": "First"}, {"name": "Second"}, {"name": "Third"}]
        
        result = service.select_by_index(places, 1)
        assert result["name"] == "Second"
        
        result = service.select_by_index(places, 5)  # out of bounds
        assert result is None


class TestQueryRewriter:
    """Test query rewriting."""

    def test_rewrite_removes_stops(self):
        """Test stopwords are removed."""
        from services.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        result = rewriter.rewrite("find a coffee shop near me")
        
        assert "find" not in result[0].lower()
        assert "near" not in result[0].lower()

    def test_rewrite_expands_queries(self):
        """Test query expansion."""
        from services.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        result = rewriter.rewrite("starbucks")
        
        assert len(result) >= 2  # Should have expansions