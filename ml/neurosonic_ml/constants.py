"""Shared constants for the NeuroSonic EEG / emotion / music pipeline."""

FS = 256  # default sampling rate (Hz) of the synthetic demo stream
CHANNELS = ["TP9", "AF7", "AF8", "TP10"]  # 4-channel headband-style montage

# Canonical EEG bands (Hz). Boundaries vary slightly between papers.
BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}

DIMENSIONS = ["valence", "arousal", "calmness", "focus", "stress"]
LATENT_KEYS = ("valence", "arousal", "focus", "stress", "calm")

DISCLAIMER = (
    "AI-estimated emotional state from a research-inspired prototype. "
    "Not a medical diagnosis or clinical assessment."
)
