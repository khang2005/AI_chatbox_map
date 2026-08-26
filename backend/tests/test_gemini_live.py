"""Live test of current Gemini provider - compare outputs."""
import asyncio
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.gemini_provider import GeminiProvider


TEST_QUERIES = [
    "get me to a nearby starbucks",
    "how about a market",
    "the second one",
    "navigate there",
    "is it open now",
]

SAMPLE_SESSION_CONTEXT = {
    "last_user_query": "coffee nearby",
    "last_intent": {"intent": "search_places", "sub_intent": None},
    "last_results": [
        {"name": "Starbucks", "location": {"lat": 14.5995, "lng": 120.9842}, "distance_km": 0.5, "rating": 4.2},
        {"name": "Starbucks Reserve", "location": {"lat": 14.6000, "lng": 120.9850}, "distance_km": 0.8, "rating": 4.5},
    ],
    "selected_place": {"name": "Starbucks"},
}


async def test_intent_extraction(provider: GeminiProvider):
    print("=" * 60)
    print("INTENT EXTRACTION TEST")
    print("=" * 60)
    
    for query in TEST_QUERIES:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        start = time.time()
        try:
            intent = await provider.extract_intent(query, SAMPLE_SESSION_CONTEXT)
            elapsed = (time.time() - start) * 1000
            
            print(f"Time: {elapsed:.0f}ms")
            print(f"Output: {json.dumps(intent, indent=2)}")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"Time: {elapsed:.0f}ms")
            print(f"Error: {e}")


async def test_response_generation(provider: GeminiProvider):
    print("\n" + "=" * 60)
    print("RESPONSE GENERATION TEST")
    print("=" * 60)
    
    sample_places = [
        {"name": "Starbucks", "distance_km": 0.5, "rating": 4.2, "vicinity": "123 Main St", "is_open": True},
        {"name": "Starbucks Reserve", "distance_km": 0.8, "rating": 4.5, "vicinity": "456 Oak Ave", "is_open": True},
    ]
    
    for query in TEST_QUERIES[:3]:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        start = time.time()
        try:
            response = await provider.generate_response(
                user_query=query,
                places=sample_places,
                directions=None,
                intent={"intent": "search_places"}
            )
            elapsed = (time.time() - start) * 1000
            
            print(f"Time: {elapsed:.0f}ms")
            print(f"Response: {response}")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"Time: {elapsed:.0f}ms")
            print(f"Error: {e}")


async def main():
    print("GEMINI PROVIDER LIVE TEST")
    print("=" * 60)
    
    try:
        provider = GeminiProvider()
        print("Provider initialized successfully")
    except Exception as e:
        print(f"Failed to initialize provider: {e}")
        return
    
    await test_intent_extraction(provider)
    await test_response_generation(provider)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
