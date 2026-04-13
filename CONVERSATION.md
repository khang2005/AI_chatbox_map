# AI Map Chatbox - Project Evolution

## Current Status (2026-04-13)

The app is running and working:
- **Backend**: http://localhost:8000 ✅ (original)
- **Frontend**: http://localhost:3000 ✅
- **Refactored Backend**: http://localhost:8001 (new modular architecture)

## To Start Fresh

```bash
# Kill anything on ports
fuser -k 3000/tcp 8000/tcp 8001/tcp 2>/dev/null

# Terminal 1 - Backend (original, stable)
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && npm start

# Terminal 3 - New refactored backend (experimental)
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Refactoring Summary (2026-04-13)

### What Was Done

The backend was refactored from a monolithic 621-line `main.py` into a clean modular architecture:

**Old Architecture Issues:**
- 621 lines in single file
- No structured intent extraction (regex-based)
- Query cleaning mixed with search
- No session/memory for follow-ups
- Response tightly coupled
- No ranking layer
- Hard to test

**New Architecture:**
```
backend/
├── main.py                    # App entry (71 lines)
├── api/
│   ├── routes_chat.py         # /api/chat endpoint
│   └── routes_health.py     # health checks
├── schemas/
│   └── chat.py              # Pydantic models
├── services/
│   ├── orchestrator.py      # Full pipeline (176 lines)
│   ├── query_rewriter.py   # Query expansion
│   ├── place_search_service.py
│   ├── route_service.py
│   ├── ranking_service.py   # Multi-factor scoring
│   ├── memory_service.py  # Session state
│   └── response_service.py
├── providers/
│   ├── gemini_provider.py   # Intent + response
│   └── mapbox_provider.py
└── utils/
    ├── config.py
    └── polyline.py
```

### Pipeline Flow

```
User Query → API → Orchestrator
  → Intent (Gemini, structured JSON)
  → Query Rewrite (multiple search terms)
  → Place Search (Mapbox + fallback)
  → Ranking (distance 35%, POI 25%, text 20%, type 10%, session 10%)
  → Route (if needed)
  → Response (Gemini)
  → Memory Update
  → Frontend
```

### Key Features Implemented

1. **Structured Intent Extraction** - Gemini returns JSON like:
```json
{"intent": "search_places", "sub_intent": "quiet", "search_terms": ["coffee", "cafe"], "filters": {}}
```

2. **Query Rewriting** - Expands "starbucks" → ["starbucks", "coffee shop", "cafe"]

3. **Ranking Service** - Multi-factor scoring (distance, POI match, text match, type, session relevance)

4. **Memory Service** - Stores session state for follow-ups like "show me the second one"

5. **Response Generation** - Gemini explains results after search/ranking (not as search engine)

### Tests

All 11 tests passing:
```bash
cd backend && source .venv/bin/activate
pytest tests/ -v
```

---

## Previous Issues Fixed (2026-04-12)

### 1. Map Not Rendering
- **Problem**: Leaflet map failed with "Invalid LatLng object: (undefined, undefined)"
- **Cause**: useEffect cleanup destroying map, mapCenter undefined
- **Fix**: Default center, validation for undefined coords

### 2. Query Cleaning
- **Problem**: "navigate me to starbucks nearby" wrong results
- **Fix**: Added "nearby", "take me" to triggers

### 3. Distant Results
- **Problem**: Returns results 4000km away
- **Fix**: 30km radius filter, fallback search

### 4. Package Issues
- **Fix**: Installed leaflet

---

## Test Queries (working)

- "where am i" → Reverse geocode address
- "coffee nearby" → Local coffee places
- "navigate me to starbucks" → Route
- "starbucks on milliken ave" → Fallback to local

---

## Migration Plan

1. Run new backend on port 8001
2. Test with frontend (change REACT_APP_API_BASE)
3. When stable, switch port 8000 → 8001
4. Deprecate old main.py

---

*Last updated: 2026-04-13*