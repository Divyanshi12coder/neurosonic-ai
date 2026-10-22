"""SQLAlchemy models: User, UserPreference, EEGSession, EEGSignal, EmotionPrediction, MoodHistory,
MusicSession, GeneratedTrack, Recommendation, Feedback."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base

Json = JSON().with_variant(JSONB(), "postgresql")


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(60))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    sessions: Mapped[list["EEGSession"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    tracks: Mapped[list["GeneratedTrack"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    genres: Mapped[list] = mapped_column(Json, default=list)
    default_mode: Mapped[str] = mapped_column(String(10), default="match")
    default_duration_s: Mapped[int] = mapped_column(Integer, default=24)
    store_features: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped[User] = relationship(back_populates="preferences")


class EEGSession(Base):
    __tablename__ = "eeg_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(20))  # demo | csv | json
    scenario: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fs: Mapped[float] = mapped_column(Float)
    channels: Mapped[list] = mapped_column(Json)
    duration_s: Mapped[float] = mapped_column(Float)
    n_windows: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(Json, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    signals: Mapped[list["EEGSignal"]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True, order_by="EEGSignal.t0")
    predictions: Mapped[list["EmotionPrediction"]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True)


class EEGSignal(Base):
    """Per-window extracted features. Raw samples are intentionally NOT stored (privacy + size)."""
    __tablename__ = "eeg_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("eeg_sessions.id", ondelete="CASCADE"), index=True)
    t0: Mapped[float] = mapped_column(Float)
    quality: Mapped[float] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(Json)
    session: Mapped[EEGSession] = relationship(back_populates="signals")


class EmotionPrediction(Base):
    __tablename__ = "emotion_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("eeg_sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("eeg_signals.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    valence: Mapped[float] = mapped_column(Float)
    arousal: Mapped[float] = mapped_column(Float)
    calmness: Mapped[float] = mapped_column(Float)
    focus: Mapped[float] = mapped_column(Float)
    stress: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(80))
    model_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    session: Mapped[EEGSession | None] = relationship(back_populates="predictions")


class MoodHistory(Base):
    __tablename__ = "mood_history"
    __table_args__ = (Index("ix_mood_user_ts", "user_id", "ts"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    valence: Mapped[float] = mapped_column(Float)
    arousal: Mapped[float] = mapped_column(Float)
    calmness: Mapped[float] = mapped_column(Float)
    focus: Mapped[float] = mapped_column(Float)
    stress: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(20))  # eeg | fused | feedback
    session_id: Mapped[int | None] = mapped_column(ForeignKey("eeg_sessions.id", ondelete="SET NULL"), nullable=True)


class MusicSession(Base):
    __tablename__ = "music_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    target: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shift: Mapped[float] = mapped_column(Float, default=0.0)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[dict] = mapped_column(Json)
    profile: Mapped[dict] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="music_session", cascade="all, delete-orphan", passive_deletes=True)
    tracks: Mapped[list["GeneratedTrack"]] = relationship(back_populates="music_session")


class GeneratedTrack(Base):
    __tablename__ = "generated_tracks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    music_session_id: Mapped[int | None] = mapped_column(ForeignKey("music_sessions.id", ondelete="SET NULL"), nullable=True)
    preset_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(120))
    subtitle: Mapped[str] = mapped_column(String(200), default="")
    audio_id: Mapped[str] = mapped_column(String(40), index=True)
    duration_s: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(40))
    prompt: Mapped[str] = mapped_column(Text, default="")
    profile: Mapped[dict] = mapped_column(Json)
    saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    user: Mapped[User] = relationship(back_populates="tracks")
    music_session: Mapped[MusicSession | None] = relationship(back_populates="tracks")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    music_session_id: Mapped[int] = mapped_column(ForeignKey("music_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    preset_id: Mapped[str] = mapped_column(String(40))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(Json, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    music_session: Mapped[MusicSession] = relationship(back_populates="recommendations")


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("generated_tracks.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    mood_after: Mapped[dict | None] = mapped_column(Json, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
