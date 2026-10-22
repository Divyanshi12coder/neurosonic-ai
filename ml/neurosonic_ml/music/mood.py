"""Mood representation, multimodal fusion and the MATCH / SHIFT mood-trajectory logic."""
from __future__ import annotations

from dataclasses import asdict, dataclass

POINT_KEYS = ("valence", "arousal", "calmness", "focus", "stress")

# Target emotional states for SHIFT MY MOOD (valence/arousal follow the circumplex model of affect).
TARGETS: dict[str, dict] = {
    "calm": dict(valence=0.66, arousal=0.18, calmness=0.90, focus=0.40, stress=0.06,
                 label="Calm", blurb="Lower arousal, settled and warm"),
    "focus": dict(valence=0.60, arousal=0.46, calmness=0.62, focus=0.92, stress=0.14,
                  label="Focus", blurb="Moderate arousal, steady and uncluttered"),
    "energize": dict(valence=0.82, arousal=0.86, calmness=0.18, focus=0.60, stress=0.18,
                     label="Energize", blurb="High arousal, positive and driving"),
    "refresh": dict(valence=0.80, arousal=0.56, calmness=0.50, focus=0.50, stress=0.08,
                    label="Refresh", blurb="Bright and light, a gentle reset"),
}


def clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


@dataclass
class MoodVector:
    valence: float
    arousal: float
    energy: float
    tempo: float
    brightness: float
    calmness: float
    intensity: float

    def to_dict(self) -> dict:
        return {k: round(v, 3) for k, v in asdict(self).items()}


def mood_vector(p: dict) -> MoodVector:
    v, a, c, s = p["valence"], p["arousal"], p["calmness"], p["stress"]
    energy = clip01(0.7 * a + 0.3 * (1 - c))
    return MoodVector(
        valence=clip01(v), arousal=clip01(a), energy=energy,
        tempo=clip01(0.7 * a + 0.2 * (1 - c) + 0.1 * v),
        brightness=clip01(0.5 * v + 0.35 * a + 0.15),
        calmness=clip01(c), intensity=clip01(0.5 * a + 0.3 * s + 0.2 * energy),
    )


def point(p: dict) -> dict[str, float]:
    return {k: round(clip01(p[k]), 4) for k in POINT_KEYS}


def lerp_point(a: dict, b: dict, t: float) -> dict[str, float]:
    return {k: round(a[k] + (b[k] - a[k]) * t, 4) for k in POINT_KEYS}


def fuse(eeg: dict | None, eeg_confidence: float, text_state: dict | None, text_weight: float = 0.3,
         history_prior: dict | None = None, history_weight: float = 0.08) -> tuple[dict, dict]:
    """Late fusion of EEG estimate, language-derived state and a small historical prior.

    Weights are reported so the UI can show how much each modality contributed.
    """
    parts: list[tuple[str, dict, float]] = []
    if eeg is not None:
        parts.append(("eeg", eeg, max(0.25, eeg_confidence) * 1.0))
    if text_state is not None:
        parts.append(("language", text_state, text_weight * (1.0 if eeg is not None else 3.0)))
    if history_prior is not None:
        parts.append(("history", history_prior, history_weight))
    if not parts:
        raise ValueError("fuse() needs at least one modality")
    total = sum(w for _, _, w in parts)
    fused = {k: sum(p[k] * w for _, p, w in parts) / total for k in POINT_KEYS}
    weights = {name: round(w / total, 3) for name, _, w in parts}
    return point(fused), weights


def plan_trajectory(current: dict, mode: str, target: str | None, shift: float, stages: int = 4) -> dict:
    """MATCH: music mirrors the current state. SHIFT: iso-principle arc that starts at the current
    state and moves progressively toward the target (shift = 0..1 how far to travel)."""
    cur = point(current)
    if mode == "match" or not target or target == "match":
        return {"mode": "match", "target_key": None, "current": cur, "target": cur, "music": cur,
                "shift": 0.0, "trajectory": [cur] * 1}
    if target not in TARGETS:
        raise ValueError(f"unknown target '{target}'")
    tgt = point(TARGETS[target])
    shift = clip01(shift)
    traj = [lerp_point(cur, tgt, shift * i / (stages - 1)) for i in range(stages)]
    music = lerp_point(cur, tgt, shift * 0.6)
    return {"mode": "shift", "target_key": target, "current": cur, "target": tgt, "music": music,
            "shift": round(shift, 3), "trajectory": traj}
