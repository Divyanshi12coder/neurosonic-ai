import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.db import models as m
from app.db.session import Base, SessionLocal, engine


@pytest.fixture()
def db(client):  # `client` fixture creates the tables via the app lifespan
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        yield s


def _user(db, email):
    u = m.User(email=email, password_hash=hash_password("password123"), display_name="T")
    u.preferences = m.UserPreference(genres=["ambient"])
    db.add(u)
    db.commit()
    return u


def test_user_unique_email_and_preferences(db):
    u = _user(db, "model-test@example.com")
    assert u.preferences.genres == ["ambient"] and u.preferences.default_mode == "match"
    db.add(m.User(email="model-test@example.com", password_hash="x", display_name="dup"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_session_relationships_and_cascade(db):
    u = _user(db, "cascade@example.com")
    s = m.EEGSession(user_id=u.id, title="t", source="demo", fs=256.0, channels=["AF7"], duration_s=4.0)
    db.add(s)
    db.flush()
    sig = m.EEGSignal(session_id=s.id, t0=0.0, quality=0.9, features={"vector": {"a": 1}})
    db.add(sig)
    db.flush()
    db.add(m.EmotionPrediction(session_id=s.id, signal_id=sig.id, user_id=u.id, valence=.5, arousal=.5, calmness=.5, focus=.5,
                               stress=.5, confidence=.5, label="x", model_name="rf"))
    db.commit()
    assert len(s.signals) == 1 and len(s.predictions) == 1 and s.created_at is not None
    db.delete(s)
    db.commit()
    assert db.query(m.EEGSignal).filter_by(session_id=s.id).count() == 0
    assert db.query(m.EmotionPrediction).filter_by(session_id=s.id).count() == 0


def test_track_feedback_and_recommendation_models(db):
    u = _user(db, "tracks@example.com")
    ms = m.MusicSession(user_id=u.id, mode="match", plan={"a": 1}, profile={"bpm": 70})
    db.add(ms)
    db.flush()
    db.add(m.Recommendation(music_session_id=ms.id, user_id=u.id, preset_id="slow-tide", rank=1, score=.9, reasons=["r"]))
    t = m.GeneratedTrack(user_id=u.id, music_session_id=ms.id, preset_id="slow-tide", title="Slow Tide", audio_id="abc", duration_s=8, provider="local-synth", profile={"bpm": 70})
    db.add(t)
    db.flush()
    db.add(m.Feedback(user_id=u.id, track_id=t.id, rating=5, mood_after={"valence": .7}))
    db.add(m.MoodHistory(user_id=u.id, valence=.5, arousal=.5, calmness=.5, focus=.5, stress=.5, label="Calm", source="eeg"))
    db.commit()
    assert t.saved is False and ms.recommendations[0].rank == 1 and t.profile["bpm"] == 70
    db.delete(u)
    db.commit()
    assert db.query(m.GeneratedTrack).filter_by(user_id=u.id).count() == 0


def test_jwt_and_hashing():
    h = hash_password("hunter2hunter2")
    assert verify_password("hunter2hunter2", h) and not verify_password("nope", h) and h != "hunter2hunter2"
    tok = create_access_token(42)
    assert decode_token(tok) == 42 and decode_token(tok + "x") is None and decode_token("garbage") is None
