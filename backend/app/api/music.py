from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from neurosonic_ml.music.catalog import CATALOG
from neurosonic_ml.music.mood import TARGETS, POINT_KEYS
from neurosonic_ml.emotion.model import describe_state

from ..db.models import Feedback, GeneratedTrack, MoodHistory, MusicSession, Recommendation, User
from ..db.session import get_db
from ..schemas import FeedbackIn, GenerateIn, GenerateOut, RecommendIn, RecommendOut, SaveTrackIn, TrackOut
from ..services import engine
from .deps import current_user, optional_user

router = APIRouter(prefix="/music", tags=["music"])


def _user_ctx(db: Session, user: User | None) -> dict:
    if not user:
        return {}
    favs = {r for r in db.scalars(select(GeneratedTrack.preset_id).where(GeneratedTrack.user_id == user.id, GeneratedTrack.saved))}
    rows = db.execute(select(GeneratedTrack.preset_id, func.avg(Feedback.rating)).join(Feedback, Feedback.track_id == GeneratedTrack.id)
                      .where(GeneratedTrack.user_id == user.id).group_by(GeneratedTrack.preset_id)).all()
    recent = db.scalars(select(MoodHistory).where(MoodHistory.user_id == user.id).order_by(MoodHistory.ts.desc()).limit(20)).all()
    prior = {k: sum(getattr(r, "calmness" if k == "calmness" else k) for r in recent) / len(recent) for k in POINT_KEYS} if len(recent) >= 5 else None
    return {"favorites": favs, "ratings": {pid: float(avg) for pid, avg in rows}, "history_prior": prior,
            "prefs": list(user.preferences.genres) if user.preferences else []}


def _run(body: RecommendIn, db: Session, user: User | None) -> dict:
    try:
        return engine.recommend(body, _user_ctx(db, user))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


def _log(db: Session, user: User, body: RecommendIn, rec: dict) -> MusicSession:
    ms = MusicSession(user_id=user.id, mode=rec["plan"]["mode"], target=rec["plan"]["target_key"], shift=rec["plan"]["shift"],
                      text=body.text, plan=rec["plan"], profile=rec["profile"])
    db.add(ms)
    db.flush()
    for i, t in enumerate(rec["tracks"][:5]):
        db.add(Recommendation(music_session_id=ms.id, user_id=user.id, preset_id=t["id"], rank=i + 1, score=t["score"], reasons=t["reasons"]))
    f = rec["fused_state"]
    db.add(MoodHistory(user_id=user.id, source="fused", label=describe_state(f)[0], session_id=body.session_id, **f))
    return ms


@router.post("/recommend", response_model=RecommendOut)
def recommend(body: RecommendIn, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    rec = _run(body, db, user)
    if user:
        rec["music_session_id"] = _log(db, user, body, rec).id
        db.commit()
    return rec


def _track_out(t: GeneratedTrack | None, *, audio_id: str, preset: dict, profile: dict, provider: str, prompt: str,
               duration: float, saved=False, variation=0) -> TrackOut:
    ext = (engine.find_audio(audio_id).suffix if engine.find_audio(audio_id) else ".wav")
    return TrackOut(id=t.id if t else None, audio_id=audio_id, audio_url=f"/api/music/audio/{audio_id}{ext}", title=preset["title"],
                    subtitle=preset["subtitle"], preset_id=preset["id"], duration_s=duration, provider=provider, prompt=prompt,
                    profile=profile, artwork=engine.artwork(preset["id"], profile, variation), saved=saved,
                    created_at=t.created_at if t else None)


@router.post("/generate", response_model=GenerateOut)
def generate(body: GenerateIn, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    rec = _run(body, db, user)
    try:
        preset = engine.choose_preset(rec, body.preset_id)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    audio_id, audio, note = engine.render_audio(rec, preset, body.duration_s, body.provider, body.variation)
    provider = audio.provider if audio else ("local-synth" if body.provider == "local-synth" or note else body.provider)
    prompt = audio.prompt if audio else ""
    from neurosonic_ml.music.profile import profile_to_prompt
    prompt = prompt or profile_to_prompt(rec["profile"])
    row = None
    if user:
        ms = _log(db, user, body, rec)
        rec["music_session_id"] = ms.id
        row = GeneratedTrack(user_id=user.id, music_session_id=ms.id, preset_id=preset["id"], title=preset["title"],
                             subtitle=preset["subtitle"], audio_id=audio_id, duration_s=float(body.duration_s),
                             provider=provider, prompt=prompt, profile=rec["profile"])
        db.add(row)
        db.commit()
    track = _track_out(row, audio_id=audio_id, preset=preset, profile=rec["profile"], provider=provider, prompt=prompt,
                       duration=float(body.duration_s), variation=body.variation)
    return GenerateOut(track=track, recommendation=rec, provider_note=note)


@router.get("/audio/{filename}")
def audio(filename: str):
    stem, _, ext = filename.partition(".")
    f = engine.find_audio(stem)
    if not f or (ext and f.suffix.lstrip(".") != ext):
        raise HTTPException(404, "Audio not found")
    return FileResponse(f, media_type=engine.MEDIA.get(f.suffix.lstrip("."), "audio/wav"), headers={"Cache-Control": "public, max-age=86400"})


@router.get("/catalog")
def catalog():
    return CATALOG


@router.get("/targets")
def targets():
    return TARGETS


def _own_track(db: Session, user: User, track_id: int) -> GeneratedTrack:
    t = db.get(GeneratedTrack, track_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Track not found")
    return t


@router.post("/save", response_model=TrackOut)
def save(body: SaveTrackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _own_track(db, user, body.track_id)
    t.saved = body.saved
    db.commit()
    return _row_out(t)


def _row_out(t: GeneratedTrack) -> TrackOut:
    from neurosonic_ml.music.recommend import get_preset
    preset = get_preset(t.preset_id) or {"id": t.preset_id, "title": t.title, "subtitle": t.subtitle}
    return _track_out(t, audio_id=t.audio_id, preset={**preset, "title": t.title, "subtitle": t.subtitle}, profile=t.profile,
                      provider=t.provider, prompt=t.prompt, duration=t.duration_s, saved=t.saved)


@router.get("/history", response_model=list[TrackOut])
def history(saved_only: bool = False, limit: int = Query(50, ge=1, le=200), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(GeneratedTrack).where(GeneratedTrack.user_id == user.id)
    if saved_only:
        q = q.where(GeneratedTrack.saved)
    return [_row_out(t) for t in db.scalars(q.order_by(GeneratedTrack.created_at.desc()).limit(limit))]


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _own_track(db, user, body.track_id)
    after = body.mood_after.model_dump() if body.mood_after else None
    db.add(Feedback(user_id=user.id, track_id=body.track_id, rating=body.rating, mood_after=after, comment=body.comment))
    if body.mood_after:
        m = body.mood_after
        db.add(MoodHistory(user_id=user.id, source="feedback", label=describe_state(m.model_dump())[0], valence=m.valence,
                           arousal=m.arousal, calmness=m.calmness, focus=m.focus, stress=m.stress))
    db.commit()
    return {"ok": True}
