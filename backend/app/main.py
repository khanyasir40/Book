from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import User, Favorite, SearchHistory, Preference
from .auth import get_password_hash
import os

# Create DB schema
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartShelf")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed admin and test users on startup
@app.on_event("startup")
def seed_users():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin1234")
    test_email = os.getenv("TEST_USER_EMAIL", "test@example.com")
    test_password = os.getenv("TEST_USER_PASSWORD", "test1234")
    db = SessionLocal()
    try:
        for (email, name, password) in [
            (admin_email, "Admin", admin_password),
            (test_email, "Test User", test_password),
        ]:
            if not email or not password:
                continue
            u = db.query(User).filter(User.email == email).first()
            if not u:
                # bcrypt limits passwords to 72 bytes; we keep test passwords short
                truncated_password = password[:72] if password else ""
                u = User(email=email, name=name, password_hash=get_password_hash(truncated_password))
                db.add(u)
                db.commit()
                print(f"Created user: {email}")
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

# Register routers
from .routes import auth as auth_routes  # noqa
from .routes import books as books_routes  # noqa
from .routes import favorites as favorites_routes  # noqa
from .routes import history as history_routes  # noqa
from .routes import profile as profile_routes  # noqa
from .routes import admin as admin_routes  # noqa

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(books_routes.router, prefix="/api/books", tags=["books"])
app.include_router(favorites_routes.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(history_routes.router, prefix="/api/history", tags=["history"])
app.include_router(profile_routes.router, prefix="/api/users", tags=["users"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])

# Serve frontend
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SmartShelf backend is running."}

# Temporary endpoint to create test user
@app.get("/create_test_user")
def create_test_user():
    """Temporary endpoint to create a test user with email 'test' and password '12345'"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test").first()
        if existing_user:
            return {"message": "Test user already exists"}
        
        # Create test user with email "test" and password "12345"
        test_user = User(
            email="test",
            name="Test User",
            password_hash=get_password_hash("12345")
        )
        db.add(test_user)
        db.commit()
        return {"message": "Test user created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating test user: {str(e)}")
    finally:
        db.close()