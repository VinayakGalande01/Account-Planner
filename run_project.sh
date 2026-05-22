#!/bin/bash

# Function to handle cleanup on script exit (Ctrl+C)
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to ensure clean termination
trap cleanup SIGINT SIGTERM

echo "Starting APEX Account Planner Ecosystem..."
echo ""

# 1. Start the Backend (FastAPI)
echo "[1/2] Launching Backend Server on port 8002..."
cd backend
uvicorn main:app --reload --port 8002 &
BACKEND_PID=$!
cd ..

# 2. Start the Frontend (Next.js)
echo "[2/2] Launching Frontend Dashboard on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "--------------------------------------------------"
echo "BOTH SERVERS ARE RUNNING:"
echo "- Backend: http://localhost:8002"
echo "- Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers."
echo "--------------------------------------------------"

# Keep the script running to wait for background jobs
wait
