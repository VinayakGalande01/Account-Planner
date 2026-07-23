"""
JWT TOKEN HANDLER (auth/jwt_handler.py)
Encodes, decodes, and validates HS256 JWT access and refresh tokens
for user session management and authentication statelessness.
"""

# --- SECTION 1: Dependencies & Crypto Configuration ---
# Imports JWT crypto libraries, datetime utilities, and loads token secret keys.
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# --- SECTION 2: Access & Refresh Token Encoding ---
# Encodes payload data with expiration timestamps into signed JWT strings.
def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode.update({"token_type": "access"})
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode.update({"token_type": "refresh"})
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- SECTION 3: Token Decoding & Signature Verification ---
# Verifies JWT signatures and returns decoded payload or raises JWTError.
def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(str(e))

