# AI Map Chatbox - Project Evolution

## Current Status (2026-04-12)

The app is running but there's a port conflict issue on port 3000.

### Running Services
- **Backend**: http://localhost:8000 ✅ (working)
- **Frontend**: http://localhost:3000 (something else is using this port)

### To Start Fresh

```bash
# Kill anything on port 3000 first
fuser -k 3000/tcp

# Terminal 1 - Backend
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend  
cd frontend
npm start
```

### API Test - Working
```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "nearest park", "location": {"lat": 34.0775, "lng": -117.6897}}'
```

Returns:
- Alma Hofman Park in Montclair, CA
- 630m driving distance
- 5 turn-by-turn steps

### Features Implemented
1. IP geolocation fallback (ip-api.com)
2. Accuracy indicator (GPS/IP)
3. Route polyline on map
4. Turn-by-turn directions card
5. Mobile-responsive UI
6. Query cleaning ("find", "near me" → removes trigger words)

### Bug Fixes Applied
1. Fixed Nominatim viewbox bug (lon_min used twice)
2. Changed Mapbox search to primary (was Nominatim, returned wrong results)
3. Fixed Mapbox Directions API `steps: "true"` (string not boolean)

### Files Modified
- `frontend/src/App.js` - Full rewrite with directions card
- `frontend/src/App.css` - Mobile-first styles
- `frontend/src/hooks/useGeolocation.js` - IP fallback + accuracy
- `backend/main.py` - Query cleaning + Mapbox priority + turn-by-turn

### Test Queries
- "nearest park" → Alma Hofman Park, Montclair
- "find coffee" → Starbucks nearby
- "get me to [place]" → turn-by-turn directions
- "where am i" → reverse geocode

---

*Last updated: 2026-04-12*