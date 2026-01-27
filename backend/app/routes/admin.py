from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from ..database import get_db
from ..models import User, Favorite, SearchHistory
from ..auth import get_current_user

router = APIRouter()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")


def require_admin(user: User) -> None:
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "created_at": u.created_at.isoformat(),
            "favorites_count": db.query(Favorite).filter(Favorite.user_id == u.id).count(),
        }
        for u in users
    ]


@router.get("/users/{user_id}/favorites")
def user_favorites(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    return [
        {
            "id": f.id,
            "book_id": f.book_id,
            "created_at": f.created_at.isoformat(),
        }
        for f in favs
    ]


@router.get("/history")
def recent_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    items = (
        db.query(SearchHistory)
        .order_by(SearchHistory.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": h.id,
            "user_id": h.user_id,
            "query": h.query,
            "filters_json": h.filters_json,
            "created_at": h.created_at.isoformat(),
        }
        for h in items
    ]


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()
    return {"message": "User deleted"}