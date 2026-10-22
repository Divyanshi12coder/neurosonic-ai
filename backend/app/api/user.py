from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import EEGSession, Feedback, GeneratedTrack, MoodHistory, MusicSession, User, UserPreference
from ..db.session import get_db
from ..schemas import PreferencesIn, PreferencesOut, ProfileOut, UserOut
from .deps import current_user
from .music import _row_out

router = APIRouter(prefix="/user", tags=["user"])


def _prefs(user: User, db: Session) -> UserPreference:
    if not user.preferences:
        user.preferences = UserPreference()
        db.commit()
    return user.preferences


@router.get("/profile", response_model=ProfileOut)
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _prefs(user, db)
    return ProfileOut(user=UserOut.model_validate(user), preferences=PreferencesOut(
        genres=p.genres or [], default_mode=p.default_mode, default_duration_s=p.default_duration_s, store_features=p.store_features))


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(body: PreferencesIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _prefs(user, db)
    p.genres, p.default_mode = body.genres, body.default_mode
    p.default_duration_s, p.store_features = body.default_duration_s, body.store_features
    db.commit()
    return PreferencesOut(**body.model_dump())


@router.get("/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(get_db)):
    count = lambda model, *w: db.scalar(select(func.count()).select_from(model).where(*w)) or 0  # noqa: E731
    mood = db.scalars(select(MoodHistory).where(MoodHistory.user_id == user.id).order_by(MoodHistory.ts.desc()).limit(300)).all()
    mood = list(reversed(mood))
    sessions = db.scalars(select(MusicSession).where(MusicSession.user_id == user.id)).all()
    avg = db.scalar(select(func.avg(Feedback.rating)).where(Feedback.user_id == user.id))
    shifts = []
    for fb, tr in db.execute(select(Feedback, GeneratedTrack).join(GeneratedTrack, GeneratedTrack.id == Feedback.track_id)
                             .where(Feedback.user_id == user.id, Feedback.mood_after.is_not(None)).order_by(Feedback.created_at.desc()).limit(20)):
        ms = db.get(MusicSession, tr.music_session_id) if tr.music_session_id else None
        if ms:
            cur = ms.plan["current"]
            shifts.append({"track_id": tr.id, "title": tr.title, "before": {"valence": cur["valence"], "arousal": cur["arousal"]},
                           "after": {"valence": fb.mood_after["valence"], "arousal": fb.mood_after["arousal"]}})
    favs = db.scalars(select(GeneratedTrack).where(GeneratedTrack.user_id == user.id, GeneratedTrack.saved)
                      .order_by(GeneratedTrack.created_at.desc()).limit(12)).all()
    return {
        "totals": {"sessions": count(EEGSession, EEGSession.user_id == user.id), "tracks": count(GeneratedTrack, GeneratedTrack.user_id == user.id),
                   "saved": count(GeneratedTrack, GeneratedTrack.user_id == user.id, GeneratedTrack.saved),
                   "feedback": count(Feedback, Feedback.user_id == user.id), "mood_logs": len(mood)},
        "mood_trend": [{"ts": m.ts, "valence": m.valence, "arousal": m.arousal, "calmness": m.calmness, "focus": m.focus,
                        "stress": m.stress, "label": m.label} for m in mood],
        "state_distribution": dict(Counter(m.label for m in mood)),
        "target_usage": dict(Counter((s.target or "match") for s in sessions)),
        "avg_rating": round(float(avg), 2) if avg is not None else None,
        "mood_shift": shifts,
        "favorite_tracks": [_row_out(t).model_dump(mode="json") for t in favs],
    }
