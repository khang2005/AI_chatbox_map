# AI Map Chatbox

An AI-powered chatbot with an interactive map for location-based queries, powered by Google Gemini and Mapbox.

## Features

- **AI Chatbot**: Gemini-powered conversational assistant
- **Interactive Map**: Leaflet map with Mapbox tiles
- **Location Search**: Find places by query or proximity
- **Routing**: Get directions between locations
- **Session Memory**: Context-aware follow-up queries

## Architecture

```
frontend/          # React SPA (Port 3000)
backend/           # FastAPI server (Port 8000)
  ├── api/         # Route handlers
  ├── schemas/     # Pydantic models
  ├── services/    # Business logic (orchestrator, search, ranking, routing, memory)
  ├── providers/   # External APIs (Gemini, Mapbox)
  └── utils/       # Config, helpers
```

## Tech Stack

- **Frontend**: React, Leaflet, TypeScript
- **Backend**: FastAPI, Python
- **AI**: Google Gemini
- **Maps**: Mapbox

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Mapbox API key
- Gemini API key

### Environment Setup

**Frontend** (`frontend/.env`):
```
REACT_APP_MAPBOX_TOKEN=your_mapbox_token
```

**Backend** (`backend/.env`):
```
MAPBOX_ACCESS_TOKEN=your_mapbox_token
GEMINI_API_KEY=your_gemini_api_key
```

### Running Locally

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm start
```

### Docker

```bash
docker-compose up --build
```

### Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

## Example Queries

- "where am i" - Reverse geocode current location
- "coffee nearby" - Find local coffee shops
- "navigate me to starbucks" - Get route to destination
- "starbucks on milliken ave" - Search specific location
