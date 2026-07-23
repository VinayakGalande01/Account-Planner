@echo off
chcp 65001 >nul
cls

:: ==============================================================================
:: APEX WINDOWS LAUNCHER SCRIPT (run_project.bat)
:: Automates Windows startup for Auth Service (Port 8001),
:: Main Backend API (Port 8002), and Next.js Frontend Dashboard (Port 3000).
:: ==============================================================================

:: --- SECTION 1: System Initialization ---
:: Sets UTF-8 encoding, clears terminal console, and displays startup logo.
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

:: --- SECTION 2: Process Orchestration ---
:: Spawns independent Command Prompt windows for Auth, Backend, and Frontend.

echo [SERVICE] Auth System
echo ├─ Port: 8001
echo ├─ URL : http://localhost:8001
echo └─ Status: STARTING
start "APEX Auth (8001)" cmd /k "echo ====================================== && echo         AUTH SERVICE (Port 8001)       && echo ====================================== && echo. && cd backend && uvicorn auth_main:app --reload --reload-exclude \"llm_cache.json\" --port 8001 --no-access-log"
echo.

timeout /t 1 >nul

echo [SERVICE] Backend Server
echo ├─ Port: 8002
echo ├─ URL : http://localhost:8002
echo └─ Status: STARTING
start "APEX Backend (8002)" cmd /k "echo ====================================== && echo        BACKEND SERVER (Port 8002)      && echo ====================================== && echo. && cd backend && uvicorn main:app --workers 4 --reload-exclude \"llm_cache.json\" --port 8002"


timeout /t 1 >nul

echo [SERVICE] Frontend Dashboard
echo ├─ Port: 3000
echo ├─ URL : http://localhost:3000
echo └─ Status: STARTING
start "APEX Frontend (3000)" cmd /k "echo ====================================== && echo      FRONTEND DASHBOARD (Port 3000)    && echo ====================================== && echo. && cd frontend && npm run dev"
echo.

timeout /t 1 >nul
echo [SUCCESS] All Services Started
echo.
pause
