"""Pydantic request/response models. This file is the API contract for the frontend."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Scenario = Literal["auto", "calm", "focused", "stressed", "excited", "drowsy", "melancholic"]
Target = Literal["calm", "focus", "energize", "refresh"]
Mode = Literal["match", "shift"]


# ---------- auth / user ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=60)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    is_demo: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PreferencesIn(BaseModel):
    genres: list[str] = Field(default_factory=list, max_length=10)
    default_mode: Mode = "match"
    default_duration_s: int = Field(24, ge=8, le=60)
    store_features: bool = True

    @field_validator("genres")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        return [g.strip().lower()[:24] for g in v if g.strip()]


class PreferencesOut(PreferencesIn):
    pass


class ProfileOut(BaseModel):
    user: UserOut
    preferences: PreferencesOut


# ---------- EEG ----------
class QualityOut(BaseModel):
    overall: float
    per_channel: list[float]
    label: str


class EmotionEstimate(BaseModel):
    """AI-estimated emotional state. NOT a medical diagnosis."""
    valence: float
    arousal: float
    calmness: float
    focus: float
    stress: float
    confidence: float
    label: str
    quadrant: str
    feature_importance: list[dict[str, Any]]
    model: dict[str, Any]


class AnalysisOut(BaseModel):
    fs: float
    channels: list[str]
    n_samples: int
    duration_s: float
    t: float | None = None
    scenario: str | None = None
    simulated_state: dict[str, float] | None = Field(None, description="Ground-truth latent used by the demo simulator (demo only)")
    quality: QualityOut
    features: dict[str, Any]
    waveform: dict[str, Any]  # {fs, channels: {name: [µV...]}}
    emotion: EmotionEstimate


class AnalyzeIn(BaseModel):
    samples: dict[str, list[float]]
    fs: float = Field(gt=0)


class SessionCreateIn(BaseModel):
    title: str | None = Field(None, max_length=120)
    scenario: Scenario = "auto"
    duration_s: int = Field(40, ge=8, le=180)
    seed: int = Field(7, ge=0, le=10_000_000)


class WindowSummary(BaseModel):
    t0: float
    quality: float
    relative_band_power: dict[str, float]
    emotion: dict[str, Any]


class SessionOut(BaseModel):
    id: int
    title: str
    source: str
    scenario: str | None
    fs: float
    channels: list[str]
    duration_s: float
    n_windows: int
    summary: dict[str, Any]
    windows: list[WindowSummary] = []
    created_at: datetime


class PredictIn(BaseModel):
    features: dict[str, float]
    quality: float = Field(1.0, ge=0, le=1)


# ---------- NLP ----------
class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TextAnalysis(BaseModel):
    provider: str
    text: str
    emotions: list[str]
    intent: str | None
    desired_transition: dict[str, str] | None
    music_preferences: list[str]
    context: list[str]
    state_estimate: dict[str, float] | None
    confidence: float


# ---------- music ----------
class MoodPoint(BaseModel):
    valence: float = Field(ge=0, le=1)
    arousal: float = Field(ge=0, le=1)
    calmness: float = Field(0.5, ge=0, le=1)
    focus: float = Field(0.5, ge=0, le=1)
    stress: float = Field(0.3, ge=0, le=1)
    confidence: float = Field(0.7, ge=0, le=1)


class RecommendIn(BaseModel):
    emotion: MoodPoint | None = Field(None, description="Current estimated state (from EEG). Optional if `text` is given.")
    mode: Mode = "match"
    target: Target | None = None
    shift: float = Field(1.0, ge=0, le=1, description="How far toward the target to travel (SHIFT mode)")
    text: str | None = Field(None, max_length=2000)
    prefs: list[str] = Field(default_factory=list, max_length=10)
    session_id: int | None = None
    quality: str | None = None
    feature_importance: list[dict[str, Any]] | None = None


class PresetOut(BaseModel):
    id: str
    title: str
    subtitle: str
    genre: str
    timbre: str
    tags: list[str]
    point: dict[str, float]
    score: float
    fit: float
    reasons: list[str]
    stage: int | None = None


class RecommendOut(BaseModel):
    fused_state: dict[str, float]
    fusion_weights: dict[str, float]
    plan: dict[str, Any]  # {mode,target_key,current,target,music,shift,trajectory[]}
    profile: dict[str, Any]
    trajectory_profiles: list[dict[str, Any]]
    mood_vector: dict[str, float]
    tracks: list[PresetOut]
    playlist: list[PresetOut]
    nlp: TextAnalysis | None
    explanation: dict[str, Any]
    music_session_id: int | None = None


class GenerateIn(RecommendIn):
    preset_id: str | None = None
    duration_s: int = Field(24, ge=8, le=60)
    provider: Literal["local-synth", "huggingface-musicgen"] = "local-synth"
    variation: int = Field(0, ge=0, le=1000, description="Change to regenerate a different take")


class TrackOut(BaseModel):
    id: int | None
    audio_id: str
    audio_url: str
    title: str
    subtitle: str
    preset_id: str
    duration_s: float
    provider: str
    prompt: str
    profile: dict[str, Any]
    artwork: dict[str, Any]
    saved: bool = False
    created_at: datetime | None = None


class GenerateOut(BaseModel):
    track: TrackOut
    recommendation: RecommendOut
    provider_note: str | None = None


class SaveTrackIn(BaseModel):
    track_id: int
    saved: bool = True


class FeedbackIn(BaseModel):
    track_id: int
    rating: int = Field(ge=1, le=5)
    mood_after: MoodPoint | None = None
    comment: str | None = Field(None, max_length=500)


# ---------- guide ----------
class ChatContext(BaseModel):
    emotion: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    context: ChatContext | None = None


class ChatOut(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    inference: list[str]
    provider: str
    embedder: str
    disclaimer: str


class HealthOut(BaseModel):
    status: str
    version: str
    database: str
    emotion_model: dict[str, Any]
    llm: str
    music_providers: list[str]
    embedder: str
