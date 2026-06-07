from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
import os
from auth.service import AuthService
from auth.dependencies import get_current_user
from schemas.auth import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

# Check if secure cookies are required (default to False for localhost development)
SECURE_COOKIE = os.getenv("SECURE_COOKIE", "False").lower() in ("true", "1")

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, service: AuthService = Depends()):
    return service.create_user(user)

@router.post("/login", response_model=Token)
def login(response: Response, credentials: UserLogin, service: AuthService = Depends()):
    token_data, refresh_token = service.authenticate_user(credentials)
    
    # Set the refresh token in an HTTP-only secure cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=SECURE_COOKIE,
        samesite="lax",
        max_age=7 * 24 * 3600,  # 7 days in seconds
    )
    
    return token_data

@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, service: AuthService = Depends()):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    
    try:
        from auth.jwt_handler import decode_access_token, create_access_token, create_refresh_token
        payload = decode_access_token(refresh_token)
        token_type = payload.get("token_type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        user_id = int(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user = service.get_user_by_id(user_id)
    if not user:
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
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    
    return Token(access_token=new_access_token, token_type="bearer")

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user = Depends(get_current_user)):
    return current_user
