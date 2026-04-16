"""Query rewriting service - expands user query into multiple search terms."""
import logging
from typing import List

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Expands a single user query into multiple search queries for better recall."""

    # Common query expansions
    EXPANSIONS = {
        "coffee": ["coffee", "cafe", "coffee shop", "espresso"],
        "starbucks": ["starbucks", "coffee shop", "cafe"],
        "restaurant": ["restaurant", "food", "dining"],
        "gas": ["gas station", "fuel", "gas"],
        "pharmacy": ["pharmacy", "drugstore", "chemist"],
        "grocery": ["grocery store", "supermarket", "food market"],
        "bank": ["bank", "atm", "banking"],
        "hotel": ["hotel", "inn", "motel", "lodging"],
    }

    # Stopwords to remove
    STOPWORDS = {
        "a", "an", "the", "to", "in", "of", "for", "with",
        "near", "nearby", "nearest", "closest", "find", "get",
        "me", "show", "look", "search", "can", "you", "i", "want",
        "please", "some", "any", "place", "spot", "location"
    }

    # Route trigger phrases to remove
    ROUTE_TRIGGERS = [
        "get me to", "take me to", "route to", "directions to",
        "navigate to", "navigate me to", "drive to", "walk to",
        "bike to", "take me", "how to get", "how do i get"
    ]

    def rewrite(self, query: str, intent_data: dict = None) -> List[str]:
        """
        Expand query into multiple search terms.
        
        Args:
            query: Original user query
            intent_data: Optional intent data from Gemini
            
        Returns:
            List of search queries to try
        """
        cleaned = self._clean_query(query)
        
        # If we have search terms from intent, use those
        if intent_data and intent_data.get("search_terms"):
            return intent_data["search_terms"]
        
        # Otherwise, generate expansions
        queries = [cleaned]
        
        # Check for known categories and expand
        query_lower = cleaned.lower()
        for key, expansions in self.EXPANSIONS.items():
            if key in query_lower:
                queries.extend(expansions)
                break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)
        
        # Limit to 4 queries max
        return unique_queries[:4]

    def _clean_query(self, query: str) -> str:
        """Clean query by removing trigger phrases and stopwords."""
        text = query.lower().strip()
        
        # Remove route triggers
        for trigger in self.ROUTE_TRIGGERS:
            text = text.replace(trigger, " ")
        
        # Remove stopwords
        words = text.split()
        words = [w for w in words if w not in self.STOPWORDS]
        
        return " ".join(words).strip()


# Singleton
_query_rewriter: "QueryRewriter" = None


def get_query_rewriter() -> QueryRewriter:
    global _query_rewriter
    if _query_rewriter is None:
        _query_rewriter = QueryRewriter()
    return _query_rewriter