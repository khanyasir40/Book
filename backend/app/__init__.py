# SmartShelf backend package

# Import and initialize the FastAPI app
from .main import app

# Import routes
from .routes import auth as auth_routes
from .routes import books as books_routes

# Register routers (separate statements since include_router returns None)
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(books_routes.router, prefix="/api/books", tags=["books"])