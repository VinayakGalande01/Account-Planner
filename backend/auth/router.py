from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
import os
import time
import uuid
from datetime import datetime
from auth.service import AuthService
from auth.dependencies import get_current_user
from schemas.auth import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

# Check if secure cookies are required (default to False for localhost development)
SECURE_COOKIE = os.getenv("SECURE_COOKIE", "False").lower() in ("true", "1")
SAMESITE_COOKIE = os.getenv("SAMESITE_COOKIE", "lax")

def log_auth_event(action: str, email: str, status_msg: str, jwt_issued: bool, response_time_ms: int):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req_id = f"auth_{uuid.uuid4().hex[:6]}"
    
    jwt_status = "YES" if jwt_issued else "NO"
    status_icon = "✅" if status_msg == "SUCCESS" else "❌"
    
    log_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 AUTHENTICATION EVENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Timestamp    : {timestamp}
Request ID   : {req_id}

Action       : {action}
Email        : {email}

Status       : {status_msg} {status_icon}

JWT Issued   : {jwt_status}
Expires In   : 24 Hours

Response Time: {response_time_ms}ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    print(log_msg)

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, service: AuthService = Depends()):
    start_time = time.time()
    try:
        new_user = service.create_user(user)
        log_auth_event("SIGNUP", user.email, "SUCCESS", False, int((time.time() - start_time) * 1000))
        return new_user
    except Exception as e:
        log_auth_event("SIGNUP", user.email, "FAILED", False, int((time.time() - start_time) * 1000))
        raise e

@router.post("/login", response_model=Token)
def login(response: Response, credentials: UserLogin, service: AuthService = Depends()):
    start_time = time.time()
    try:
        token_data, refresh_token = service.authenticate_user(credentials)
        
        # Set the refresh token in an HTTP-only secure cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=SECURE_COOKIE,
            samesite=SAMESITE_COOKIE,
            max_age=7 * 24 * 3600,  # 7 days in seconds
        )
        
        log_auth_event("LOGIN", credentials.email, "SUCCESS", True, int((time.time() - start_time) * 1000))
        return token_data
    except Exception as e:
        log_auth_event("LOGIN", credentials.email, "FAILED", False, int((time.time() - start_time) * 1000))
        raise e

@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, service: AuthService = Depends()):
    start_time = time.time()
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        log_auth_event("REFRESH", "Unknown User", "FAILED (No Token)", False, int((time.time() - start_time) * 1000))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    
    try:
        from auth.jwt_handler import decode_access_token, create_access_token, create_refresh_token
        payload = decode_access_token(refresh_token)
        token_type = payload.get("token_type")
        if token_type != "refresh":
            log_auth_event("REFRESH", "Unknown User", "FAILED (Invalid Type)", False, int((time.time() - start_time) * 1000))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            log_auth_event("REFRESH", "Unknown User", "FAILED (Invalid Sub)", False, int((time.time() - start_time) * 1000))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        user_id = int(user_id_str)
    except Exception:
        log_auth_event("REFRESH", "Unknown User", "FAILED (Expired Token)", False, int((time.time() - start_time) * 1000))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user = service.get_user_by_id(user_id)
    if not user:
        log_auth_event("REFRESH", f"ID:{user_id}", "FAILED (Not Found)", False, int((time.time() - start_time) * 1000))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=SECURE_COOKIE,
        samesite=SAMESITE_COOKIE,
        max_age=7 * 24 * 3600,
    )
    
    log_auth_event("REFRESH", user.email, "SUCCESS", True, int((time.time() - start_time) * 1000))
    return Token(access_token=new_access_token, token_type="bearer")

@router.post("/logout")
def logout(response: Response, current_user = Depends(get_current_user)):
    start_time = time.time()
    response.delete_cookie("refresh_token")
    # Using getattr to safely handle case where current_user might not be full model if decoded differently
    email = getattr(current_user, 'email', 'Unknown User')
    log_auth_event("LOGOUT", email, "SUCCESS", False, int((time.time() - start_time) * 1000))
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user = Depends(get_current_user)):
    start_time = time.time()
    email = getattr(current_user, 'email', 'Unknown User')
    log_auth_event("SESSION VERIFY", email, "SUCCESS", False, int((time.time() - start_time) * 1000))
    return current_user
