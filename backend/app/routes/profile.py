from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from ..database import get_db
from ..models import Preference
from ..auth import get_current_user

router = APIRouter()

@router.get("/preferences")
def get_preferences(db: Session = Depends(get_db), user=Depends(get_current_user)):
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()
    prefs = json.loads(pref.preferences_json) if pref else {}
    return {"preferences": prefs}

@router.post("/preferences")
def save_preferences(preferences: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()
    if pref:
        pref.preferences_json = json.dumps(preferences)
    else:
        pref = Preference(user_id=user.id, preferences_json=json.dumps(preferences))
        db.add(pref)
    db.commit()
    return {"message": "Saved"}