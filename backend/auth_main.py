import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(override=True)

# Ensure backend path is recognized
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.router import router as auth_router

app = FastAPI(title="APEX Auth Microservice")

# Configure CORS
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
