"""
AUTHENTICATION INTEGRATION TEST (test_auth.py)
Integration test script using FastAPI TestClient to verify user signup registration
and login token generation routines against the auth microservice.
"""

# --- SECTION 1: Dependencies & Test Client Setup ---
# Imports FastAPI TestClient and initializes app instance.
from fastapi.testclient import TestClient
from auth_main import app

client = TestClient(app)

# --- SECTION 2: Signup & Login Test Execution ---
# Tests signup endpoint creation and validates login token authentication responses.
print("Testing Signup...")
signup_data = {
    "name": "Test User",
    "email": "testuser@example.com",
    "password": "Password123!"
}
response = client.post("/auth/signup", json=signup_data)
print("Signup Response Code:", response.status_code)
print("Signup Response JSON:", response.json())

print("Testing Login...")
login_data = {
    "email": "testuser@example.com",
    "password": "Password123!"
}
response = client.post("/auth/login", json=login_data)
print("Login Response Code:", response.status_code)
print("Login Response JSON:", response.json())
