"""Rule-based language understanding for mood descriptions (always available, no API key).

Extracts emotions, intent, desired transition, music preferences and context from free text,
and converts the emotional language into an estimated mood point that can be fused with EEG.
When an LLM provider is configured, `llm_refine` asks it for the same schema and merges the result.
"""
from __future__ import annotations

import json
import re

from ..music.mood import TARGETS, POINT_KEYS, clip01

# word -> (valence, arousal) on 0..1 ; coarse affect lexicon (circumplex model)
EMOTION_LEXICON: dict[str, tuple[float, float]] = {
    "exhausted": (0.30, 0.10), "tired": (0.38, 0.12), "sleepy": (0.50, 0.08), "drained": (0.28, 0.12),
    "burnt out": (0.22, 0.20), "burned out": (0.22, 0.20), "fatigued": (0.32, 0.12),
    "stressed": (0.22, 0.82), "anxious": (0.22, 0.82), "nervous": (0.30, 0.78), "overwhelmed": (0.18, 0.80),
    "tense": (0.26, 0.76), "angry": (0.12, 0.90), "frustrated": (0.20, 0.78), "restless": (0.35, 0.75),
    "worried": (0.25, 0.70), "panicked": (0.10, 0.94),
    "sad": (0.15, 0.22), "down": (0.22, 0.20), "lonely": (0.18, 0.20), "gloomy": (0.20, 0.20), "melancholy": (0.22, 0.25),
    "bored": (0.35, 0.18), "numb": (0.30, 0.15),
    "calm": (0.70, 0.18), "relaxed": (0.75, 0.15), "peaceful": (0.78, 0.12), "content": (0.75, 0.30),
    "serene": (0.78, 0.10), "chill": (0.70, 0.22),
    "happy": (0.88, 0.60), "joyful": (0.92, 0.68), "excited": (0.85, 0.88), "energetic": (0.78, 0.86),
    "motivated": (0.78, 0.75), "pumped": (0.85, 0.92), "hopeful": (0.80, 0.45), "grateful": (0.85, 0.35),
    "focused": (0.62, 0.50), "distracted": (0.38, 0.55), "foggy": (0.35, 0.22), "scattered": (0.32, 0.65),
}
NEGATORS = {"not", "never", "no", "n't", "barely"}

INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(focus|concentrate|study|deep work|get work done|productive)\b", "focus"),
    (r"\b(calm|relax|unwind|de-?stress|settle|chill|slow down|breathe|soothe)\b", "calm"),
    (r"\b(energi[sz]\w*|pump|workout|wake up|motivat|hype|get going|power through)\b", "energize"),
    (r"\b(refresh|reset|brighten|lift my mood|cheer|uplift|feel better)\b", "refresh"),
    (r"\b(sleep|fall asleep|wind down for bed)\b", "calm"),
]
PREFERENCE_WORDS = {
    "piano": "piano", "lofi": "lofi", "lo-fi": "lofi", "ambient": "ambient", "classical": "classical",
    "electronic": "electronic", "synth": "electronic", "acoustic": "acoustic", "jazz": "jazz", "guitar": "acoustic",
    "instrumental": "instrumental", "minimal": "minimal", "cinematic": "cinematic",
}
CONTEXTS = {
    "work": r"\b(work|office|meeting|deadline|email)\b", "study": r"\b(study|studying|exam|exams|homework|reading|thesis)\b",
    "workout": r"\b(workout|gym|run|running|exercise|lift)\b", "commute": r"\b(commute|train|bus|drive|driving)\b",
    "sleep": r"\b(sleep|bed|night|insomnia)\b", "creative": r"\b(write|writing|design|paint|create|creative)\b",
    "social": r"\b(party|friends|dinner)\b",
}


def _emotions(text: str) -> list[tuple[str, tuple[float, float]]]:
    low = text.lower()
    found = []
    for word, va in sorted(EMOTION_LEXICON.items(), key=lambda kv: -len(kv[0])):
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
            before = low[max(0, m.start() - 14):m.start()]
            if any(n in before.split() or before.endswith("n't ") for n in NEGATORS):
                found.append((f"not {word}", (1 - va[0] if word in ("calm", "relaxed", "happy", "content") else va[0], 1 - va[1] if word in ("calm", "relaxed") else va[1])))
            else:
                found.append((word, va))
            break
    return found


def parse_text(text: str) -> dict:
    text = (text or "").strip()[:2000]
    low = text.lower()
    found = _emotions(text)
    emotions = [w for w, _ in found]
    intents = [t for pat, t in INTENT_PATTERNS if re.search(pat, low)]
    intent = intents[0] if intents else None
    prefs = sorted({v for k, v in PREFERENCE_WORDS.items() if re.search(r"\b" + re.escape(k) + r"\b", low)})
    contexts = [c for c, pat in CONTEXTS.items() if re.search(pat, low)]
    # "I feel X but I want to Y": the first clause is the current state
    state_part = re.split(r"\b(but|however|though|want|need|wish|hope|so that)\b", low, maxsplit=1)[0]
    current_found = _emotions(state_part) or found

    state = None
    if current_found:
        v = sum(va[0] for _, va in current_found) / len(current_found)
        a = sum(va[1] for _, va in current_found) / len(current_found)
        state = {
            "valence": round(clip01(v), 3), "arousal": round(clip01(a), 3),
            "calmness": round(clip01(0.9 - a * 0.8 - max(0.0, 0.5 - v) * 0.6), 3),
            "focus": 0.7 if "focused" in emotions else 0.3 if ("distracted" in emotions or "foggy" in emotions or "scattered" in emotions) else 0.45,
            "stress": round(clip01(0.5 * (1 - v) + 0.5 * a), 3),
        }
    if intent is None and state is None:
        confidence = 0.0
    else:
        confidence = round(min(1.0, 0.3 + 0.2 * len(found) + (0.3 if intent else 0)), 2)
    transition = None
    if intent and intent in TARGETS:
        transition = {"from": current_found[0][0] if current_found else "current state", "to": TARGETS[intent]["label"].lower()}
    return {
        "provider": "rules", "text": text, "emotions": emotions[:6], "intent": intent,
        "desired_transition": transition, "music_preferences": prefs, "context": contexts,
        "state_estimate": state, "confidence": confidence,
    }


def merge_llm_json(rules: dict, raw: str) -> dict:
    """Merge a JSON string returned by an LLM into the rule-based result (validated + clipped)."""
    try:
        obj = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception:  # noqa: BLE001
        return rules
    out = dict(rules)
    if isinstance(obj.get("emotions"), list):
        out["emotions"] = [str(x)[:30] for x in obj["emotions"]][:6] or out["emotions"]
    if obj.get("intent") in TARGETS:
        out["intent"] = obj["intent"]
        out["desired_transition"] = {"from": (obj.get("current_emotion") or "current state")[:30], "to": TARGETS[obj["intent"]]["label"].lower()}
    if isinstance(obj.get("music_preferences"), list):
        out["music_preferences"] = sorted(set(out["music_preferences"]) | {str(x).lower()[:20] for x in obj["music_preferences"]})[:8]
    if isinstance(obj.get("context"), list):
        out["context"] = sorted(set(out["context"]) | {str(x).lower()[:20] for x in obj["context"]})[:6]
    st = obj.get("state_estimate")
    if isinstance(st, dict) and all(k in st for k in ("valence", "arousal")):
        try:
            v, a = clip01(float(st["valence"])), clip01(float(st["arousal"]))
            out["state_estimate"] = {**(out["state_estimate"] or {}), "valence": v, "arousal": a,
                                     "calmness": clip01(1 - a * 0.8), "stress": clip01(0.5 * (1 - v) + 0.5 * a),
                                     "focus": (out["state_estimate"] or {}).get("focus", 0.45)}
        except (TypeError, ValueError):
            pass
    out["provider"] = "llm+rules"
    out["confidence"] = max(out["confidence"], 0.6)
    return out


assert set(POINT_KEYS) >= {"valence"}
