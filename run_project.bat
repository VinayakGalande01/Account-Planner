@echo off
echo Starting APEX Account Planner Ecosystem...
echo.

:: 1. Start the Backend (FastAPI)
echo [1/2] Launching Backend Server on port 8002...
start "APEX Backend (8002)" cmd /k "cd backend && uvicorn main:app --reload --port 8002"

:: 2. Start the Frontend (Next.js)
echo [2/2] Launching Frontend Dashboard on port 3000...
start "APEX Frontend (3000)" cmd /k "cd frontend && npm run dev"

echo.
echo --------------------------------------------------
echo BOTH SERVERS ARE LAUNCHING IN SEPARATE WINDOWS.
echo - Backend: http://localhost:8002
echo - Frontend: http://localhost:3000
echo.
echo You can close this window now.
echo --------------------------------------------------
pause
