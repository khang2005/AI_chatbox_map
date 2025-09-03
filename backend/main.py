from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create FastAPI app instance
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/api/chat")
async def chat(message: dict):
    user_query = message.get("text", "")
    
    try:
        # Use Gemini 2.0 Flash
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Enhanced prompt for better responses
        prompt = f"""
        You are a helpful map assistant. Respond to the user's query about locations, places, or directions.
        Keep responses concise and friendly.
        
        User query: {user_query}
        Response:
        """
        
        response = model.generate_content(prompt)
        
        return {
            "response": response.text,
            "places": []  # We'll add map data later
        }
        
    except Exception as e:
        # Minimal fallback without mock data
        return {
            "response": "I'm currently unable to process your request. Please try again later.",
            "places": []
        }

@app.get("/")
async def root():
    return {"message": "AI Map Chatbot API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
