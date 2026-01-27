from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
# Removed passlib import to avoid bcrypt compatibility issues
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
import os

SECRET_KEY = os.getenv("SECRET_KEY", "smart_shelf_dev_secret_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Removed CryptContext initialization to avoid bcrypt compatibility issues
# Using direct bcrypt calls instead
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        import bcrypt
        # Verify bcrypt hash directly
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # Return False if verification fails for any reason
        return False


def get_password_hash(password: str) -> str:
    # Direct bcrypt approach to avoid passlib overhead
    import bcrypt
    
    # bcrypt has a hard limit of 72 bytes for passwords
    if isinstance(password, str):
        # Convert to bytes first
        password_bytes = password.encode('utf-8')
        
        # Truncate to 72 bytes if necessary
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            
            # Try to decode back to UTF-8 string
            try:
                password = password_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 decode fails, fall back to ASCII printable characters
                password = ''.join(chr(b) for b in password_bytes if 32 <= b <= 126)
                # If that results in empty string, use a safe default
                if not password:
                    password = password_bytes[:32].decode('ascii', errors='ignore') or 'default_password_123'
    
    try:
        # Use bcrypt directly with controlled rounds
        salt = bcrypt.gensalt(rounds=4)  # Match the min_rounds from passlib config
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Bcrypt error: {e}")
        raise ValueError(f"Error hashing password: {str(e)}")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user