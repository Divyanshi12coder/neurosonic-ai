"""Orchestration layer: wires the ML package (EEG -> emotion -> mood -> music) to the API."""
from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np

from neurosonic_ml.constants import CHANNELS, FS
from neurosonic_ml.eeg.pipeline import analyze_window
from neurosonic_ml.eeg.synthetic import current_scenario_name, generate_window, scenario_latent
from neurosonic_ml.emotion.model import describe_state, get_default_model
from neurosonic_ml.music import mood as moodlib
from neurosonic_ml.music.explain import build_explanation
from neurosonic_ml.music.profile import mood_to_profile
from neurosonic_ml.music.providers import ProviderError, get_provider
from neurosonic_ml.music.recommend import get_preset, rank, transition_playlist
from neurosonic_ml.nlp.llm import LLMError, get_llm
from neurosonic_ml.nlp.parser import merge_llm_json, parse_text
from neurosonic_ml.rag.engine import NeuroGuide

from ..core.config import get_settings

log = logging.getLogger("neurosonic")
PALETTE = ["#2B1B16", "#4A3028", "#63463B", "#80665A", "#CBB9AC", "#E9DED6"]
EXT = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/flac": "flac", "audio/mpeg": "mp3", "audio/ogg": "ogg"}
MEDIA = {v: k for k, v in EXT.items() if k != "audio/x-wav"}


@lru_cache
def emotion_model():
    m = get_default_model()
    m.est.n_jobs = 1  # per-request inference is tiny; avoid thread-pool overhead
    return m


@lru_cache
def llm():
    s = get_settings()
    return get_llm(s.llm_api_key, s.llm_base_url, s.llm_model)


@lru_cache
def guide() -> NeuroGuide:
    return NeuroGuide(llm(), get_settings().embedding_provider)


# ---------------- EEG ----------------
def analyze_raw(raw: np.ndarray, fs: float, channels: list[str], **extra) -> dict:
    res = analyze_window(raw, fs, channels, notch_hz=get_settings().notch_hz)
    res["emotion"] = emotion_model().predict(res["features"], quality=res["quality"]["overall"])
    res.update(extra)
    return res


def demo_window(scenario: str, t: float, window_s: float = 4.0, seed: int = 7) -> dict:
    lat = scenario_latent(scenario, t + window_s / 2)
    raw = generate_window(lat, t0=t, duration=window_s, fs=FS, seed=seed)
    return analyze_raw(raw, FS, CHANNELS, t=t, scenario=current_scenario_name(scenario, t + window_s / 2),
                       simulated_state={k: round(v, 3) for k, v in lat.items()})


# ---------------- NLP ----------------
def analyze_text(text: str) -> dict:
    rules = parse_text(text)
    if llm().available():
        try:
            raw = llm().complete(
                "Extract affect from the user's message. Reply with JSON only: {\"emotions\": [str], \"current_emotion\": str, "
                "\"intent\": one of calm|focus|energize|refresh|null, \"music_preferences\": [str], \"context\": [str], "
                "\"state_estimate\": {\"valence\": 0-1, \"arousal\": 0-1}}", text, max_tokens=250, temperature=0)
            return merge_llm_json(rules, raw)
        except LLMError as e:
            log.info("LLM unavailable for NLP, using rules: %s", e)
    return rules


# ---------------- music ----------------
def _infer_target(state: dict) -> str:
    if state["stress"] > 0.55 or state["arousal"] > 0.65:
        return "calm"
    if state["arousal"] < 0.3:
        return "focus"
    return "refresh"


def recommend(p, user_ctx: dict | None = None) -> dict:
    """p: RecommendIn. user_ctx: {prefs, favorites, ratings, history_prior}."""
    user_ctx = user_ctx or {}
    nlp = analyze_text(p.text) if p.text and p.text.strip() else None
    eeg = None
    if p.emotion is not None:
        eeg = {k: getattr(p.emotion, k) for k in moodlib.POINT_KEYS}
    text_state = nlp["state_estimate"] if nlp and nlp.get("state_estimate") else None
    if eeg is None and text_state is None:
        raise ValueError("Provide an EEG-derived `emotion` or a `text` description with recognisable feelings.")
    fused, weights = moodlib.fuse(eeg, p.emotion.confidence if p.emotion else 0.0, text_state,
                                  history_prior=user_ctx.get("history_prior"))
    target = p.target
    if p.mode == "shift" and not target:
        target = (nlp or {}).get("intent") or _infer_target(fused)
    plan = moodlib.plan_trajectory(fused, p.mode, target, p.shift)
    prefs = sorted({*(x.lower() for x in p.prefs), *user_ctx.get("prefs", []), *((nlp or {}).get("music_preferences") or [])})
    profile = mood_to_profile(plan["music"], prefs)
    traj_profiles = [mood_to_profile(pt, prefs) for pt in plan["trajectory"]]
    favs, ratings = user_ctx.get("favorites"), user_ctx.get("ratings")
    tracks = rank(plan["music"], prefs, favs, ratings, k=6)
    playlist = transition_playlist(plan["trajectory"], prefs, favs, ratings) if p.mode == "shift" else tracks[:1]
    emo_ctx = {**fused, "confidence": p.emotion.confidence if p.emotion else (nlp or {}).get("confidence", 0.5),
               "label": describe_state(fused)[0], "feature_importance": p.feature_importance or []}
    explanation = build_explanation(emo_ctx if (p.emotion or text_state) else None, plan, profile, tracks[0], weights, nlp, p.quality)
    return {
        "fused_state": fused, "fusion_weights": weights, "plan": plan, "profile": profile,
        "trajectory_profiles": traj_profiles, "mood_vector": profile["mood_vector"],
        "tracks": tracks, "playlist": playlist, "nlp": nlp, "explanation": explanation, "music_session_id": None,
    }


def artwork(preset_id: str, profile: dict, variation: int = 0) -> dict:
    seed = int(hashlib.sha1(f"{preset_id}:{variation}".encode()).hexdigest()[:8], 16)
    return {"seed": seed, "palette": PALETTE, "energy": profile["energy"], "brightness": profile["brightness"],
            "bpm": profile["bpm"], "valence": profile["mood_vector"]["valence"]}


def _prune(directory: Path, keep: int = 300) -> None:
    files = sorted(directory.glob("*.*"), key=lambda f: f.stat().st_mtime)
    for f in files[:-keep]:
        f.unlink(missing_ok=True)


def find_audio(audio_id: str) -> Path | None:
    if not audio_id.isalnum():
        return None
    for ext in MEDIA:
        f = get_settings().generated_dir / f"{audio_id}.{ext}"
        if f.exists():
            return f
    return None


def render_audio(rec: dict, preset: dict, duration: int, provider_name: str, variation: int) -> tuple[str, "object", str | None]:
    """Render (or reuse cached) audio for the recommendation. Returns (audio_id, GeneratedAudio|None, note)."""
    s = get_settings()
    stages = [{**st, "timbre": preset["timbre"]} for st in (rec["trajectory_profiles"] if rec["plan"]["mode"] == "shift" else [rec["profile"]])]
    seed = int(hashlib.sha1(f"{preset['id']}:{variation}".encode()).hexdigest()[:8], 16)
    key = hashlib.sha1(json.dumps([stages, duration, seed, provider_name], sort_keys=True, default=str).encode()).hexdigest()[:20]
    cached = find_audio(key)
    if cached:
        return key, None, None
    note = None
    prov = get_provider(provider_name, s.hf_api_token)
    if provider_name != prov.name:
        note = f"{provider_name} is not configured (missing key); used the local generative synth instead."
    try:
        audio = prov.generate(stages, duration, seed, preset["timbre"])
    except ProviderError as e:
        note = f"{prov.name} failed ({e}); used the local generative synth instead."
        audio = get_provider("local-synth").generate(stages, duration, seed, preset["timbre"])
    ext = EXT.get(audio.content_type.split(";")[0], "wav")
    (s.generated_dir / f"{key}.{ext}").write_bytes(audio.wav)
    _prune(s.generated_dir)
    return key, audio, note


def choose_preset(rec: dict, preset_id: str | None) -> dict:
    if preset_id:
        pr = get_preset(preset_id)
        if not pr:
            raise ValueError(f"unknown preset '{preset_id}'")
        return pr
    return rec["tracks"][0]
