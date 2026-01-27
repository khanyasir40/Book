from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import SearchHistory
from ..auth import get_current_user

router = APIRouter()


@router.get("/recent")
def recent(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": h.id,
            "query": h.query,
            "filters_json": h.filters_json,
            "created_at": h.created_at.isoformat(),
        }
        for h in items
    ]