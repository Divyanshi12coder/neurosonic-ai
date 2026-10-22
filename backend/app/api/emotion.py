from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from neurosonic_ml.eeg.features import FEATURE_NAMES

from ..db.models import MoodHistory, User
from ..db.session import get_db
from ..schemas import EmotionEstimate, PredictIn
from ..services import engine
from .deps import current_user

router = APIRouter(tags=["emotion"])


@router.post("/emotion/predict", response_model=EmotionEstimate)
def predict(body: PredictIn):
    """Estimate emotion dimensions from an extracted feature vector (see `features.vector` of /eeg/analyze)."""
    missing = [k for k in FEATURE_NAMES if k not in body.features]
    if missing:
        raise HTTPException(422, f"Missing features: {', '.join(missing)}")
    return engine.emotion_model().predict(body.features, quality=body.quality)


@router.get("/mood/history")
def mood_history(limit: int = Query(200, ge=1, le=1000), user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(MoodHistory).where(MoodHistory.user_id == user.id).order_by(MoodHistory.ts.desc()).limit(limit)).all()
    return [{"ts": r.ts, "valence": r.valence, "arousal": r.arousal, "calmness": r.calmness, "focus": r.focus,
             "stress": r.stress, "label": r.label, "source": r.source} for r in reversed(rows)]
