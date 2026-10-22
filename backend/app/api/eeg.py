from collections import Counter
from datetime import timedelta

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from neurosonic_ml.constants import CHANNELS, FS, DIMENSIONS
from neurosonic_ml.eeg.io import EEGFormatError, Recording, parse_upload
from neurosonic_ml.eeg.pipeline import window_iter
from neurosonic_ml.eeg.synthetic import current_scenario_name, generate_window, scenario_latent

from ..core.config import get_settings
from ..db.models import EEGSession, EEGSignal, EmotionPrediction, MoodHistory, User, now
from ..db.session import get_db
from ..schemas import AnalysisOut, AnalyzeIn, Scenario, SessionCreateIn, SessionOut, WindowSummary
from ..services import engine
from .deps import current_user

router = APIRouter(prefix="/eeg", tags=["eeg"])
MAX_WINDOWS = 90


@router.get("/demo/window", response_model=AnalysisOut)
def demo_window(scenario: Scenario = "auto", t: float = Query(0, ge=0, le=1_000_000),
                window_s: float = Query(4.0, ge=2, le=8), seed: int = Query(7, ge=0, le=10_000_000)):
    """Synthetic EEG window run through the SAME pipeline as uploaded data (stateless, phase-continuous in `t`)."""
    return engine.demo_window(scenario, t, window_s, seed)


@router.post("/analyze", response_model=AnalysisOut)
def analyze(body: AnalyzeIn):
    names = list(body.samples.keys())
    if not 1 <= len(names) <= 32:
        raise HTTPException(422, "Provide between 1 and 32 channels")
    lens = {len(v) for v in body.samples.values()}
    if len(lens) != 1:
        raise HTTPException(422, "All channels must have the same number of samples")
    n = lens.pop()
    if not (body.fs * 2 <= n <= body.fs * 30):
        raise HTTPException(422, "Window must be between 2 and 30 seconds long")
    arr = np.array([body.samples[k] for k in names], dtype=float)
    if not np.isfinite(arr).all():
        raise HTTPException(422, "Samples contain NaN/Inf")
    return engine.analyze_raw(arr, body.fs, names)


def _persist(db: Session, user: User, *, title: str, source: str, scenario: str | None, fs: float, channels: list[str],
             duration: float, windows: list[dict]) -> EEGSession:
    store = user.preferences.store_features if user.preferences else True
    emos = [w["emotion"] for w in windows]
    mean = {d: round(float(np.mean([e[d] for e in emos])), 4) for d in DIMENSIONS}
    labels = Counter(e["label"] for e in emos)
    sess = EEGSession(user_id=user.id, title=title, source=source, scenario=scenario, fs=fs, channels=channels,
                      duration_s=round(duration, 2), n_windows=len(windows),
                      summary={"mean": mean, "dominant_state": labels.most_common(1)[0][0],
                               "state_counts": dict(labels), "mean_quality": round(float(np.mean([w["quality"]["overall"] for w in windows])), 3),
                               "mean_confidence": round(float(np.mean([e["confidence"] for e in emos])), 3),
                               "model": emos[0]["model"]["label"]})
    db.add(sess)
    db.flush()
    start = sess.created_at or now()
    for w in windows:
        e = w["emotion"]
        feats = {k: v for k, v in w["features"].items() if k != "psd"}
        sig = EEGSignal(session_id=sess.id, t0=w["t0"], quality=w["quality"]["overall"], features=feats if store else {"vector": feats["vector"]})
        db.add(sig)
        db.flush()
        db.add(EmotionPrediction(session_id=sess.id, signal_id=sig.id, user_id=user.id, model_name=e["model"]["name"],
                                 **{d: e[d] for d in DIMENSIONS}, confidence=e["confidence"], label=e["label"]))
        db.add(MoodHistory(user_id=user.id, ts=start - timedelta(seconds=duration - w["t0"]), source="eeg", session_id=sess.id,
                           label=e["label"], **{d: e[d] for d in DIMENSIONS}))
    db.commit()
    return sess


def _out(sess: EEGSession, with_windows: bool) -> SessionOut:
    wins: list[WindowSummary] = []
    if with_windows:
        preds = {p.signal_id: p for p in sess.predictions}
        for s in sess.signals:
            p = preds.get(s.id)
            wins.append(WindowSummary(
                t0=s.t0, quality=s.quality, relative_band_power=s.features.get("relative_band_power", {}),
                emotion={d: getattr(p, d) for d in DIMENSIONS} | {"confidence": p.confidence, "label": p.label} if p else {}))
    return SessionOut(id=sess.id, title=sess.title, source=sess.source, scenario=sess.scenario, fs=sess.fs,
                      channels=sess.channels, duration_s=sess.duration_s, n_windows=sess.n_windows, summary=sess.summary,
                      windows=wins, created_at=sess.created_at)


@router.post("/session", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Record a demo session: synthetic EEG is generated, analysed window by window and stored."""
    windows = []
    t = 0.0
    while t + 4.0 <= body.duration_s and len(windows) < MAX_WINDOWS:
        w = engine.demo_window(body.scenario, t, 4.0, body.seed)
        w["t0"] = t
        windows.append(w)
        t += 2.0
    title = body.title or f"Demo session · {current_scenario_name(body.scenario, 0).title()}"
    sess = _persist(db, user, title=title, source="demo", scenario=body.scenario, fs=FS, channels=CHANNELS,
                    duration=body.duration_s, windows=windows)
    return _out(sess, True)


@router.post("/upload", response_model=SessionOut, status_code=201)
async def upload(file: UploadFile = File(...), fs: float | None = Form(None), title: str | None = Form(None),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = get_settings().max_upload_mb * 1024 * 1024
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".json")):
        raise HTTPException(415, "Unsupported file type. Upload a .csv or .json EEG recording")
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"File too large (max {get_settings().max_upload_mb} MB)")
    try:
        rec: Recording = parse_upload(name, content, fs)
    except EEGFormatError as e:
        raise HTTPException(422, str(e)) from e
    windows = []
    for t0, w in window_iter(rec, 4.0, 2.0):
        res = engine.analyze_raw(w, rec.fs, rec.channels)
        res["t0"] = round(t0, 2)
        windows.append(res)
        if len(windows) >= MAX_WINDOWS:
            break
    sess = _persist(db, user, title=(title or file.filename or "Uploaded EEG")[:120], source=name.rsplit(".", 1)[-1], scenario=None,
                    fs=rec.fs, channels=rec.channels, duration=rec.duration, windows=windows)
    return _out(sess, True)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(limit: int = Query(30, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(EEGSession).where(EEGSession.user_id == user.id).order_by(EEGSession.created_at.desc()).limit(limit)).all()
    return [_out(r, False) for r in rows]


@router.get("/session/{session_id}", response_model=SessionOut)
def get_session(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sess = db.get(EEGSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(404, "Session not found")
    return _out(sess, True)
