@echo off
chcp 65001 >nul
cls

echo ╔══════════════════════════════════════════════╗
echo ║      APEX ACCOUNT PLANNER ECOSYSTEM          ║
echo ╚══════════════════════════════════════════════╝
echo.

echo [INFO] Initializing System...
timeout /t 1 >nul
echo [INFO] Checking Environment...
timeout /t 1 >nul
echo [INFO] Loading Configuration...
timeout /t 1 >nul
echo [SUCCESS] Environment Loaded
echo.

echo [SERVICE] Auth System
echo ├─ Port: 8001
echo ├─ URL : http://localhost:8001
echo └─ Status: STARTING
start "APEX Auth (8001)" cmd /k "cd backend && uvicorn auth_main:app --reload --port 8001 --no-access-log"
echo.

timeout /t 1 >nul

echo [SERVICE] Backend Server
echo ├─ Port: 8002
echo ├─ URL : http://localhost:8002
echo └─ Status: STARTING
start "APEX Backend (8002)" cmd /k "cd backend && uvicorn main:app --reload --port 8002"
echo.

timeout /t 1 >nul

echo [SERVICE] Frontend Dashboard
echo ├─ Port: 3000
echo ├─ URL : http://localhost:3000
echo └─ Status: STARTING
start "APEX Frontend (3000)" cmd /k "cd frontend && npm run dev"
echo.

timeout /t 1 >nul
echo [SUCCESS] All Services Started
echo.
pause
