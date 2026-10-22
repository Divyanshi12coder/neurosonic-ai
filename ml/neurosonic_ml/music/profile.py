"""Translate a mood point into concrete music parameters (the 'music profile')."""
from __future__ import annotations

from .mood import clip01, mood_vector

MODES = {
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}
ROOTS = ["C", "D", "Eb", "F", "G", "A", "Bb"]
ROOT_SEMITONE = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
DYNAMICS = [(0.2, "pp"), (0.38, "p"), (0.55, "mp"), (0.72, "mf"), (1.01, "f")]

# user-stated preferences -> main melodic timbre
TIMBRE_BY_PREF = {"piano": "piano", "acoustic": "pluck", "lofi": "piano", "electronic": "synth", "ambient": "pad",
                  "classical": "bell", "jazz": "piano"}


def mood_to_profile(p: dict, prefs: list[str] | None = None, seed_root: str | None = None) -> dict:
    prefs = [x.lower() for x in (prefs or [])]
    mv = mood_vector(p)
    v, a, c, f, s = p["valence"], p["arousal"], p["calmness"], p["focus"], p["stress"]

    bpm = int(round(min(150, max(48, 50 + 90 * mv.tempo))))
    if v >= 0.7:
        mode = "lydian" if a < 0.4 else "major"
    elif v >= 0.52:
        mode = "mixolydian"
    elif v >= 0.38:
        mode = "dorian"
    else:
        mode = "phrygian" if (a > 0.7 and v < 0.3) else "aeolian"
    root = seed_root if seed_root in ROOT_SEMITONE else ROOTS[int(v * 3 + a * 4) % len(ROOTS)]

    rhythm = clip01(0.05 + 0.9 * a)
    complexity = clip01(0.25 + 0.30 * a + 0.15 * v - 0.20 * f)
    reverb = clip01(0.3 + 0.6 * c)
    dyn = next(lbl for lim, lbl in DYNAMICS if mv.intensity < lim)

    inst = ["soft pads"] if a < 0.75 else ["warm synth pads"]
    if c > 0.5 or a < 0.3:
        inst.append("airy textures")
    if "piano" in prefs or (c > 0.55 and a < 0.5):
        inst.append("felt piano")
    if rhythm > 0.2:
        inst.append("plucked arpeggio")
    inst.append("sub bass" if a > 0.3 else "low drone")
    if v < 0.4 and a < 0.6:
        inst.append("low strings")
    if a > 0.7 and v > 0.55:
        inst.append("bright synth lead")

    if rhythm < 0.25:
        perc = "none"
    elif rhythm < 0.45:
        perc = "sparse soft pulse"
    elif rhythm < 0.7:
        perc = "steady kick + light hats"
    else:
        perc = "driving kick, hats, off-beat accents"
    if a > 0.5:
        inst.append(perc)
    texture = "sparse and airy" if rhythm < 0.3 else "layered" if rhythm < 0.65 else "dense and rhythmic"

    timbre = next((TIMBRE_BY_PREF[x] for x in prefs if x in TIMBRE_BY_PREF), "pad" if a < 0.45 else "pluck")

    tags = []
    if a < 0.3 and c > 0.6:
        tags += ["ambient", "calming", "slow tempo"]
    if f > 0.7:
        tags += ["focus", "steady pulse", "minimal"]
    if a > 0.7:
        tags += ["energetic", "driving"]
    if v > 0.65:
        tags.append("uplifting")
    if v < 0.4:
        tags.append("introspective")
    if s > 0.6:
        tags.append("de-stress")
    tags += [x for x in prefs if x not in tags][:3]
    genre = ("ambient" if a < 0.3 else "lo-fi / downtempo" if a < 0.5 and f > 0.6 else "downtempo" if a < 0.55
             else "melodic electronica" if v > 0.5 else "dark pulse")
    return {
        "bpm": bpm, "key": root, "scale": mode, "mode_name": f"{root} {mode}",
        "energy": round(mv.energy, 3), "brightness": round(mv.brightness, 3),
        "rhythm_density": round(rhythm, 3), "harmonic_complexity": round(complexity, 3),
        "dynamics": dyn, "texture": texture, "reverb": round(reverb, 3),
        "instrumentation": inst, "percussion": perc, "timbre": timbre,
        "genre": genre, "mood_tags": tags[:6],
        "mood_vector": mv.to_dict(),
    }


def profile_to_prompt(profile: dict) -> str:
    """Text prompt for text-to-music models (e.g. MusicGen)."""
    return (f"{profile['genre']} instrumental, {profile['bpm']} BPM, {profile['mode_name']}, "
            f"{profile['texture']} texture, {', '.join(profile['instrumentation'][:4])}, "
            f"{', '.join(profile['mood_tags'][:3])}, dynamics {profile['dynamics']}")
