"""Generative soundscape presets.

NeuroSonic does not ship or stream copyrighted songs. The "catalog" is a library of
generative presets: each has a character (timbre, seed, tags, a home position in
valence/arousal space) and is rendered by the music provider using the live profile.
"""
from __future__ import annotations

# id, title, subtitle, genre, timbre, (valence, arousal, calmness, focus, stress), tags
_RAW = [
    ("slow-tide", "Slow Tide", "Drifting ambient swells", "ambient", "pad", (0.66, 0.12, 0.92, 0.35, 0.05), ["ambient", "calming", "sleep"]),
    ("cedar-hour", "Cedar Hour", "Warm felt-piano stillness", "neo-classical", "piano", (0.62, 0.20, 0.85, 0.40, 0.08), ["piano", "calming", "acoustic"]),
    ("paper-lanterns", "Paper Lanterns", "Soft bells over a low drone", "ambient", "bell", (0.70, 0.22, 0.80, 0.30, 0.06), ["ambient", "classical", "calming"]),
    ("blue-hour", "Blue Hour", "Slow, wistful and spacious", "ambient", "pad", (0.32, 0.18, 0.62, 0.30, 0.30), ["introspective", "ambient"]),
    ("rain-on-glass", "Rain on Glass", "Muted piano, patient pulse", "lo-fi", "piano", (0.40, 0.26, 0.66, 0.50, 0.24), ["lofi", "piano", "introspective"]),
    ("low-orbit", "Low Orbit", "Weightless low-end and air", "ambient", "pad", (0.45, 0.30, 0.70, 0.45, 0.12), ["ambient", "electronic"]),
    ("midnight-study", "Midnight Study", "Lo-fi pulse for deep work", "lo-fi", "piano", (0.58, 0.42, 0.62, 0.90, 0.14), ["lofi", "focus", "piano"]),
    ("quiet-engine", "Quiet Engine", "Minimal steady pulse", "minimal", "pluck", (0.55, 0.48, 0.55, 0.93, 0.16), ["focus", "electronic", "minimal"]),
    ("graphite", "Graphite", "Repeating arpeggio, little change", "minimal", "pluck", (0.52, 0.50, 0.50, 0.88, 0.18), ["focus", "minimal"]),
    ("copper-lines", "Copper Lines", "Warm plucks, even tempo", "downtempo", "pluck", (0.62, 0.45, 0.58, 0.80, 0.12), ["focus", "acoustic"]),
    ("first-light", "First Light", "Gentle, rising and optimistic", "downtempo", "bell", (0.78, 0.50, 0.55, 0.50, 0.08), ["uplifting", "refresh"]),
    ("citrus-air", "Citrus Air", "Bright, airy and light", "melodic electronica", "pluck", (0.82, 0.58, 0.48, 0.48, 0.07), ["uplifting", "electronic", "refresh"]),
    ("morning-ledger", "Morning Ledger", "Clean piano and soft kick", "downtempo", "piano", (0.74, 0.54, 0.50, 0.62, 0.10), ["piano", "refresh", "uplifting"]),
    ("sunroom", "Sunroom", "Sunlit chords, easy groove", "downtempo", "piano", (0.80, 0.46, 0.60, 0.40, 0.06), ["uplifting", "acoustic"]),
    ("tidal-pulse", "Tidal Pulse", "Rolling pulse, widening harmony", "melodic electronica", "synth", (0.72, 0.70, 0.32, 0.60, 0.20), ["energetic", "electronic"]),
    ("ember-run", "Ember Run", "Driving rhythm, warm lead", "melodic electronica", "synth", (0.80, 0.84, 0.18, 0.55, 0.22), ["energetic", "electronic", "workout"]),
    ("kinetic", "Kinetic", "Fast arpeggios, bright top end", "electronica", "synth", (0.84, 0.90, 0.14, 0.52, 0.18), ["energetic", "electronic"]),
    ("overdrive-bloom", "Overdrive Bloom", "Big pulse, euphoric lift", "electronica", "synth", (0.88, 0.82, 0.16, 0.45, 0.14), ["energetic", "uplifting"]),
    ("iron-pulse", "Iron Pulse", "Tense, dark and propulsive", "dark pulse", "synth", (0.22, 0.82, 0.12, 0.48, 0.84), ["driving", "dark"]),
    ("static-bloom", "Static Bloom", "Anxious texture, slow release", "dark pulse", "pad", (0.28, 0.66, 0.24, 0.35, 0.74), ["de-stress", "dark"]),
    ("grey-corridor", "Grey Corridor", "Brooding low strings", "cinematic", "pad", (0.18, 0.40, 0.34, 0.30, 0.55), ["introspective", "cinematic"]),
    ("hush-protocol", "Hush Protocol", "Down-shifting calm for tense minds", "ambient", "pad", (0.58, 0.20, 0.82, 0.38, 0.12), ["de-stress", "ambient", "calming"]),
    ("amber-descent", "Amber Descent", "Gradual slow-down, warm piano", "neo-classical", "piano", (0.60, 0.24, 0.78, 0.42, 0.10), ["de-stress", "piano", "calming"]),
    ("glass-garden", "Glass Garden", "Crystalline bells, slow bloom", "neo-classical", "bell", (0.68, 0.32, 0.72, 0.52, 0.08), ["classical", "calming"]),
]

CATALOG = [
    {"id": i, "title": t, "subtitle": s, "genre": g, "timbre": tim,
     "point": dict(zip(("valence", "arousal", "calmness", "focus", "stress"), pt)), "tags": tags}
    for i, t, s, g, tim, pt, tags in _RAW
]
BY_ID = {c["id"]: c for c in CATALOG}
