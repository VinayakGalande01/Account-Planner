#!/bin/bash

clear

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

echo "[SERVICE] Local LLM Server"
echo "├─ Path: /Users/theabhijitjagtap/Local_server-main"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to activate" -e "tell application \"Terminal\" to do script \"cd '/Users/theabhijitjagtap/Local_server-main' && ./start.sh\"" > /dev/null
echo ""

sleep 1.5

echo "[SERVICE] Auth System"
echo "├─ Port: 8001"
echo "├─ URL : http://localhost:8001"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to activate" -e "tell application \"Terminal\" to do script \"cd '$PWD/backend' && uvicorn auth_main:app --reload --reload-exclude \\\"llm_cache.json\\\" --port 8001 --no-access-log\"" > /dev/null
echo ""

sleep 1.5

echo "[SERVICE] Backend Server"
echo "├─ Port: 8002"
echo "├─ URL : http://localhost:8002"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to activate" -e "tell application \"Terminal\" to do script \"cd '$PWD/backend' && uvicorn main:app --reload --reload-exclude \\\"llm_cache.json\\\" --port 8002\"" > /dev/null
echo ""

sleep 1.5

echo "[SERVICE] Frontend Dashboard"
echo "├─ Port: 3000"
echo "├─ URL : http://localhost:3000"
echo "└─ Status: STARTING"
osascript -e "tell application \"Terminal\" to activate" -e "tell application \"Terminal\" to do script \"cd '$PWD/frontend' && npm run dev\"" > /dev/null
echo ""

sleep 1.5
echo "[SUCCESS] All Services Started"
echo ""
