# AI Map Chatbox

This project is a web application that combines a chatbot with an interactive map. The chatbot is powered by Google's Gemini AI and is designed to assist users with location-based queries.

## Features

*   **AI Chatbot:** A chat interface to interact with a Gemini-powered AI assistant.
*   **Interactive Map:** A Google Map that displays locations.
*   **Dockerized Services:** The frontend and backend are containerized using Docker for consistent development and deployment.

## Architecture

The application is composed of two main services:

*   **Frontend:** A React single-page application that provides the user interface, including the chat window and the map. It communicates with the backend via HTTP requests.
*   **Backend:** A FastAPI server that handles the chat logic. It receives user messages from the frontend, sends them to the Gemini AI for processing, and returns the AI's response.

## Getting Started

### Prerequisites

*   Docker and Docker Compose
*   Node.js and npm (for local frontend development)
*   Python (for local backend development)
*   Google Maps API Key
*   Gemini API Key

### Installation and Running

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Set up environment variables:**
    *   Create a `.env` file in the `frontend` directory with your Google Maps API key:
        ```
        REACT_APP_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
        ```
    *   Create a `.env` file in the `backend` directory with your Gemini API key:
        ```
        GEMINI_API_KEY=your_gemini_api_key
        ```

3.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.
