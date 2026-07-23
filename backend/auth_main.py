"""
STANDALONE AUTH MICROSERVICE (auth_main.py)
Microservice entrypoint exposing user authentication endpoints,
CORS policies, and dedicated healthcheck endpoints independently of the main API server.
"""

# --- SECTION 1: Dependencies & App Setup ---
# Loads environment variables, initializes FastAPI instance, and includes auth routers.
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.router import router as auth_router

app = FastAPI(title="APEX Auth Microservice")

# --- SECTION 2: CORS Middleware & Health Check Endpoints ---
# Configures dynamic origins for frontend cross-origin requests and microservice health routing.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/api/health")
def auth_health():
    return {"status": "operational", "service": "auth"}

