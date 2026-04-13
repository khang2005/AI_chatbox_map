# AI Map Chatbox - Project Evolution

## Current Status (2026-04-12)

The app is running and working. Both services running locally:
- **Backend**: http://localhost:8000 ✅
- **Frontend**: http://localhost:3000 ✅

## To Start Fresh

```bash
# Kill anything on ports
fuser -k 3000/tcp 8000/tcp 2>/dev/null

# Terminal 1 - Backend
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && npm start
```

## Issues Fixed

### 1. Map Not Rendering
- **Problem**: Leaflet map failed with "Invalid LatLng object: (undefined, undefined)"
- **Cause**: useEffect cleanup destroying map on every re-render, and mapCenter being undefined on first render
- **Fix**: Initialize map with hardcoded default center (34.0775, -117.6897) immediately, added validation for undefined/null coordinates

### 2. Query Cleaning
- **Problem**: "navigate me to starbucks nearby" passed full query to Mapbox returning wrong results
- **Cause**: "nearby" and "take me" not in ROUTE_TRIGGERS
- **Fix**: Added "nearby", "take me" to triggers, added stopword removal (a, an, the, to, etc.)

### 3. Distant Results
- **Problem**: "starbucks on milliken ave" returned Starbucks in Canada (4000km away) instead of nearby
- **Cause**: Mapbox returns global results for specific queries
- **Fix**: Added distance filtering (30km radius), fallback search with simpler queries when no nearby results found

### 4. Package Issues
- **Problem**: leaflet not installed
- **Fix**: Ran `npm install leaflet react-leaflet`

## Files Modified
- `frontend/src/App.js` - Map initialization fixes, coordinate validation
- `frontend/src/App.css` - Min-height for map container
- `backend/main.py` - Query cleaning, distance filtering, fallback search
- `CONVERSATION.md` - This file

## Test Queries
- "where am i" → Reverse geocode address
- "coffee nearby" → Local coffee places
- "navigate me to starbucks" → Route to nearest Starbucks
- "starbucks on milliken ave" → Fallback to nearest Starbucks (within 30km)

---

*Last updated: 2026-04-12*