from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import requests
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Initialize APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def search_places(query: str, location: Optional[dict] = None, radius: int = 5000):
    """Search locations using Google Places API"""
    params = {
        "query": query,
        "key": GOOGLE_MAPS_API_KEY
    }
    if location:
        params["location"] = f"{location['lat']},{location['lng']}"
        params["radius"] = radius
    
    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params=params
    )
    return response.json()

@app.post("/api/chat")
async def chat(message: dict):
    try:
        user_query = message.get("text", "")
        model = genai.GenerativeModel('gemini-pro')
        
        # Location-based queries
        location_keywords = ["near me", "find", "where is", "nearby"]
        if any(kw in user_query.lower() for kw in location_keywords):
            places_data = search_places(user_query)
            
            prompt = f"""
            Respond as a friendly travel assistant. 
            User asked: "{user_query}"
            
            Found these places:
            {chr(10).join([f"- {p['name']} ({p.get('rating', '?')}★)" for p in places_data.get('results', [])[:3]])}
            
            Guidelines:
            1. Mention top 3 options
            2. Include ratings if available
            3. Add emojis when appropriate
            """
            
            response = model.generate_content(prompt)
            
            return {
                "response": response.text,
                "places": places_data.get("results", [])
            }
        
        # General queries
        response = model.generate_content(user_query)
        return {"response": response.text}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
