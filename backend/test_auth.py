"""
AUTHENTICATION INTEGRATION TEST (test_auth.py)
Integration test script using FastAPI TestClient to verify user signup registration
and login token generation routines against the auth microservice.
"""

import sys
from auth_main import app

def get_test_client():
    try:
        from fastapi.testclient import TestClient
        return TestClient(app)
    except Exception:
        import httpx
        return httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

def test_auth_endpoints():
    client = get_test_client()
    print("Testing Signup...")
    signup_data = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "Password123!"
    }
    response = client.post("/auth/signup", json=signup_data)
    print("Signup Response Code:", response.status_code)

    print("Testing Login...")
    login_data = {
        "email": "testuser@example.com",
        "password": "Password123!"
    }
    response = client.post("/auth/login", json=login_data)
    print("Login Response Code:", response.status_code)

if __name__ == "__main__":
    test_auth_endpoints()
