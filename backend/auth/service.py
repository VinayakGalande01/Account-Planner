"""
AUTHENTICATION SERVICE (auth/service.py)
Encapsulates business logic for user creation, credential verification,
user query resolution, and JWT token pair generation.
"""

# --- SECTION 1: Service Dependencies & Imports ---
# Imports ORM session dependencies, password security utilities, and schema models.
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.auth import UserCreate, UserLogin, UserResponse, Token
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_access_token, create_refresh_token

# --- SECTION 2: User Persistence & Authentication Logic ---
# Handles database queries, user account registration with hashed passwords, and login tokens.
class AuthService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, payload: UserCreate) -> User:
        if self.get_user_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        hashed = hash_password(payload.password)
        db_user = User(name=payload.name, email=payload.email, hashed_password=hashed)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate_user(self, payload: UserLogin) -> tuple[Token, str]:
        user = self.get_user_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return Token(access_token=access_token, token_type="bearer"), refresh_token


