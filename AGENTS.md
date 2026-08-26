# AGENTS.md

This file provides guidelines for agentic coding agents operating in this repository.

## Build/Lint/Test Commands

*   **Start Services (Docker):** `docker compose up -d --build`
*   **Stop Services:** `docker compose down`
*   **View Logs:** `docker compose logs -f`
*   **Test:** `cd backend && source .venv/bin/activate && PYTHONPATH=. pytest tests/ -v`
*   **Run a single test:** `pytest <test_file_path> -k <test_name>`
*   **Frontend:** http://localhost:3000
*   **Backend API:** http://localhost:8000
*   **Health Check:** http://localhost:8000/health

## Code Style Guidelines

*   **Language:** Python
*   **Imports:** Follow standard Python import conventions.
*   **Formatting:** Adhere to PEP 8 style guidelines.
*   **Types:** Use type hints for function arguments and return values.
*   **Naming Conventions:** Use snake_case for variable and function names. Use PascalCase for class names.
*   **Error Handling:** Implement appropriate try-except blocks for error handling.
*   **File Structure:** Organize code into logical modules and packages.

## Architecture

```
backend/
├── main.py                    # FastAPI entry
├── api/                      # Route handlers
│   ├── routes_chat.py
│   └── routes_health.py
├── schemas/                  # Pydantic models
│   ├── chat.py
│   ├── places.py
│   └── session.py
├── services/                 # Business logic
│   ├── orchestrator.py       # Main pipeline coordinator
│   ├── intent_service.py     # Intent extraction
│   ├── memory_service.py     # Session memory (JSON persistence)
│   ├── place_search_service.py
│   ├── ranking_service.py
│   ├── route_service.py
│   └── response_service.py
├── providers/                # External APIs
│   ├── gemini_provider.py
│   └── mapbox_provider.py
├── utils/
│   ├── config.py
│   └── polyline.py
└── data/                     # Persistence
    └── session_memory.json

frontend/                     # React SPA (Port 3000)
```

## Pipeline Flow

```
User Query → Intent (Gemini) → Query Rewrite → Place Search → Ranking → Route (if needed) → Response (Gemini) → Memory Update
```

## Session Memory Behavior

* Follow-up modes: `select`, `refine`, `replace_search`, `none`
* Category switches (market, mall, cafe, etc.) trigger fresh searches
* Explicit references ("the second one", "navigate there") reuse previous results
* Routes cleared on replacement searches
* JSON persistence at `backend/data/session_memory.json`

## Example Queries

* "where am i" → Reverse geocode address
* "coffee nearby" → Local coffee places
* "navigate me to starbucks" → Route
* "the second one" → Select from previous results
* "how about a market" → Fresh search (not follow-up)

## Rules

* Keep route handlers thin, business logic in services
* Use type hints everywhere
* Do not introduce MySQL for session memory (Redis-ready design)
* Design MemoryService so RedisMemoryService can implement same interface
