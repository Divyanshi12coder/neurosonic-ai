"""Rank generative presets for a mood point, with light personalisation."""
from __future__ import annotations

import math

from .catalog import BY_ID, CATALOG
from .mood import POINT_KEYS

WEIGHTS = {"valence": 1.0, "arousal": 1.3, "calmness": 0.7, "focus": 0.9, "stress": 0.6}
_MAX = math.sqrt(sum(WEIGHTS.values()))


def _dist(a: dict, b: dict) -> float:
    return math.sqrt(sum(WEIGHTS[k] * (a[k] - b[k]) ** 2 for k in POINT_KEYS))


def rank(point: dict, prefs: list[str] | None = None, favorites: set[str] | None = None,
         ratings: dict[str, float] | None = None, exclude: set[str] | None = None, k: int = 5) -> list[dict]:
    """score = mood fit (0..1) + preference-tag bonus + favourite bonus + learned rating bonus."""
    prefs = {p.lower() for p in (prefs or [])}
    favorites = favorites or set()
    ratings = ratings or {}
    out = []
    for c in CATALOG:
        if exclude and c["id"] in exclude:
            continue
        fit = 1 - _dist(point, c["point"]) / _MAX
        tag_hits = sorted(prefs & {t.lower() for t in c["tags"]} | ({c["genre"]} & prefs))
        bonus_pref = 0.05 * len(tag_hits)
        bonus_fav = 0.04 if c["id"] in favorites else 0.0
        bonus_rating = 0.06 * ((ratings.get(c["id"], 3.0) - 3.0) / 2.0)  # 1..5 stars
        score = fit + bonus_pref + bonus_fav + bonus_rating
        reasons = [f"mood fit {fit:.0%}"]
        if tag_hits:
            reasons.append("matches your preferences: " + ", ".join(tag_hits))
        if bonus_fav:
            reasons.append("you saved this before")
        if bonus_rating > 0:
            reasons.append("you rated similar sounds highly")
        elif bonus_rating < 0:
            reasons.append("down-weighted from your past ratings")
        out.append({**c, "score": round(score, 4), "fit": round(fit, 4), "reasons": reasons})
    out.sort(key=lambda r: -r["score"])
    return out[:k]


def transition_playlist(trajectory: list[dict], prefs=None, favorites=None, ratings=None) -> list[dict]:
    """One preset per trajectory stage (iso principle), avoiding repeats."""
    chosen: list[dict] = []
    used: set[str] = set()
    for i, pt in enumerate(trajectory):
        best = rank(pt, prefs, favorites, ratings, exclude=used, k=1)[0]
        used.add(best["id"])
        chosen.append({**best, "stage": i + 1})
    return chosen


def get_preset(preset_id: str) -> dict | None:
    return BY_ID.get(preset_id)
