from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth.jwt_handler import decode_access_token
from auth.service import AuthService
from models.user import User
from database import current_user_id_var

# OAuth2 scheme expects a token endpoint at /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), service: AuthService = Depends()) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        token_type = payload.get("token_type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception
    user = service.get_user_by_id(user_id)
    if not user:
        raise credentials_exception
    
    # Set context variable for DB Row-Level Security
    current_user_id_var.set(str(user.id))
    
    # Thread-safe attachment of user context to the database session
    if hasattr(service, "db") and service.db:
        service.db.info["user_id"] = str(user.id)
    
    return user
