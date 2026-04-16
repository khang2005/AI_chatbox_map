#!/bin/bash

# Kill existing services
echo "Stopping existing services..."
fuser -k 3000/tcp 8000/tcp 8001/tcp 2>/dev/null
sleep 1

# Create data directory if needed
mkdir -p backend/data

# Start backend
echo "Starting backend on port 8000..."
cd backend && source .venv/bin/activate && export $(cat .env | xargs) && nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Start frontend
echo "Starting frontend on port 3000..."
cd ../frontend && nohup npm start > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

# Wait and verify
sleep 3
echo ""
echo "Services:"
ss -tlnp | grep -E '3000|8000' | awk '{print "  Port " $4 " - running"}'

echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Logs:"
echo "  Backend:  tail -f /tmp/backend.log"
echo "  Frontend: tail -f /tmp/frontend.log"
