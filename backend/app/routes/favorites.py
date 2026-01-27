from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from ..database import get_db
from ..models import Favorite
from ..schemas import FavoriteIn, FavoriteOut
from ..auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[FavoriteOut])
def list_favorites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    return [FavoriteOut(id=f.id, book_id=f.book_id, book_json=json.loads(f.book_json)) for f in favs]


@router.post("/", response_model=FavoriteOut)
def add_favorite(fav_in: FavoriteIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.book_id == fav_in.book_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")
    fav = Favorite(user_id=user.id, book_id=fav_in.book_id, book_json=json.dumps(fav_in.book_json))
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return FavoriteOut(id=fav.id, book_id=fav.book_id, book_json=json.loads(fav.book_json))


@router.delete("/{book_id}")
def remove_favorite(book_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    fav = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.book_id == book_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")
    db.delete(fav)
    db.commit()
    return {"message": "Removed"}