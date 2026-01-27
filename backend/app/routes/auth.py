from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserOut, TokenOut, LoginIn
from ..auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Validate all required fields are present
    if not user_in.name or not user_in.email or not user_in.password:
        raise HTTPException(status_code=400, detail="All fields (name, email, password) are required")
    
    # Check if email already exists
    try:
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        
        # Create new user
        user = User(email=user_in.email, name=user_in.name, password_hash=get_password_hash(user_in.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        # Handle database connection issues
        if "database" in str(e).lower() or "connection" in str(e).lower():
            raise HTTPException(status_code=503, detail="Database connection unavailable. Please try again later.")
        # Re-raise other exceptions
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenOut)
def login(user_in: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user