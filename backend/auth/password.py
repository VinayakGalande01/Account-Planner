"""
PASSWORD SECURITY UTILITIES (auth/password.py)
Provides secure bcrypt hashing and password verification routines
for user account registration and login authentication.
"""

# --- SECTION 1: Dependencies & Import ---
# Imports bcrypt crypto library for salted password hashing.
import bcrypt

# --- SECTION 2: Password Hashing & Verification ---
# Hashes plain-text passwords with salt and verifies input matches stored hashes.
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False

