# AI Map Chatbox - Project Evolution

## Conversation Summary

### Initial State
- **Project**: AI-powered map chatbot using Google Maps + Gemini AI
- **Issue**: API keys were exposed in .env files and git history

### Security Fixes Applied
1. Removed hardcoded API keys from `.env` files
2. Deleted backup file (`main.py.backup`)
3. Scrubbed git history using `git-filter-repo`
4. Force pushed to remote repository

### Migration to Free Alternatives

| Component | Before (Paid) | After (Free) |
|-----------|---------------|--------------|
| Map API | Google Maps ($) | Mapbox (25K/mo free) |
| Map Display | Google Maps JS | Leaflet + OpenStreetMap |
| AI Model | Gemini AI | Ollama + Llama 3 |

### Current Issues (Unresolved)

1. **Mapbox Search API** - Returns wrong locations (e.g., "Fine Street, Tennessee" instead of local California results)
   - Root cause: Mapbox geocoding API doesn't prioritize nearby POIs well
   - Need to add Nominatim as fallback

2. **Ollama Connection** - Docker container can't connect to host's Ollama service
   - Tried: host network mode, host.docker.internal, various IPs
   - Ollama only listens on 127.0.0.1

3. **AI Responses** - Fallback to basic responses due to Ollama connection failure

### Files Modified

#### Backend (`backend/`)
- `main.py` - Rewrote with Mapbox API calls + Ollama integration
- `requirements.txt` - Removed google-generativeai, googlemaps
- `.env` - Changed to MAPBOX_ACCESS_TOKEN, OLLAMA_HOST

#### Frontend (`frontend/`)
- `src/App.js` - Replaced @react-google-maps/api with Leaflet
- `package.json` - Replaced leaflet-free dependencies
- `.env` - Added REACT_APP_API_BASE

#### Config
- `docker-compose.yml` - Fixed .env path, tried host network mode for Ollama

### Setup Instructions (Current)

1. **Mapbox**: Get token at https://mapbox.com
2. **Ollama**: 
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama run llama3
   ```
3. **Configure**:
   ```bash
   # backend/.env
   MAPBOX_ACCESS_TOKEN=your_mapbox_token
   OLLAMA_HOST=http://localhost:11434
   ```
4. **Run**: `docker-compose up --build`

### Proposed Fix Plan (On Hold)

| Component | Action |
|-----------|--------|
| **Place Search** | Add Nominatim as primary (free, reliable OSM) |
| **Directions** | Keep Mapbox Directions API |
| **Geocoding** | Keep Mapbox (for "where am I") |
| **AI** | Switch back to Gemini API (new key needed) |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/chat` | POST | Chat with map context |

### Chat Request Format
```json
{
  "text": "find coffee near me",
  "location": {"lat": 40.7128, "lng": -74.0060},
  "mode": "driving"
}
```

### Response Format
```json
{
  "response": "AI generated response",
  "places": [{"name": "...", "location": {...}}],
  "directions": [{"polyline": "...", "distance_text": "..."}]
}
```

---

*Generated on: 2026-04-09*
*Last updated: AI Chatbox Migration + Mapbox Search Issues*