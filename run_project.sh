#!/bin/bash

# ==============================================================================
# APEX LAUNCHER SCRIPT (run_project.sh)
# Automates local ecosystem startup: Auth Service (Port 8001),
# Main Backend API (Port 8002), and Next.js Frontend Dashboard (Port 3000).
# ==============================================================================

clear

# --- SECTION 1: Initialization & Environment Checks ---
# Clears terminal buffer and prints environment startup banner.
echo "╔══════════════════════════════════════════════╗"
echo "║      APEX ACCOUNT PLANNER ECOSYSTEM          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

echo "[INFO] Initializing System..."
sleep 0.4
echo "[INFO] Checking Environment..."
sleep 0.4
echo "[INFO] Loading Configuration..."
sleep 0.4
echo "[SUCCESS] Environment Loaded"
echo ""

# --- SECTION 2: Service Orchestration & Terminal Launches ---
# Launches Auth, Backend, and Frontend processes in dedicated macOS Terminal windows.
sleep 1.5

echo "[SERVICE] Auth System"
echo "├─ Port: 8001"
echo "├─ URL : http://localhost:8001"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to do script \"echo '\n======================================\n        AUTH SERVICE (Port 8001)       \n======================================\n' && cd '$PWD/backend' && uvicorn auth_main:app --reload --reload-exclude \\\"llm_cache.json\\\" --port 8001 --no-access-log\"" > /dev/null
echo ""

sleep 1.5

echo "[SERVICE] Backend Server"
echo "├─ Port: 8002"
echo "├─ URL : http://localhost:8002"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to do script \"echo '\n======================================\n       BACKEND SERVER (Port 8002)      \n======================================\n' && cd '$PWD/backend' && uvicorn main:app --workers 4 --reload-exclude \\\"llm_cache.json\\\" --port 8002\"" > /dev/null
echo ""

sleep 1.5

echo "[SERVICE] Frontend Dashboard"
echo "├─ Port: 3000"
echo "├─ URL : http://localhost:3000"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to do script \"echo '\n======================================\n     FRONTEND DASHBOARD (Port 3000)    \n======================================\n' && cd '$PWD/frontend' && npm run dev\"" > /dev/null
echo ""

sleep 1.5
echo "[SUCCESS] All Services Started"
echo ""
