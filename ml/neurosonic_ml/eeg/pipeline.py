"""End-to-end EEG analysis: raw window -> filtered signal -> quality -> features."""
from __future__ import annotations

import numpy as np

from .features import extract_features
from .io import Recording
from .preprocessing import preprocess, signal_quality


def analyze_window(raw: np.ndarray, fs: float, channels: list[str], notch_hz: float | None = 50.0, waveform_hz: int = 128) -> dict:
    """Run the full pipeline on one window. Returns features + quality + a decimated waveform."""
    raw = np.asarray(raw, dtype=float)
    filtered = preprocess(raw, fs, notch_hz=notch_hz)
    quality = signal_quality(raw, filtered, fs)
    features = extract_features(filtered, fs, channels)
    step = max(1, int(round(fs / waveform_hz)))
    return {
        "fs": fs,
        "channels": channels,
        "n_samples": int(raw.shape[1]),
        "duration_s": round(raw.shape[1] / fs, 3),
        "quality": quality,
        "features": features,
        "waveform": {"fs": fs / step, "channels": {c: np.round(filtered[i, ::step], 2).tolist() for i, c in enumerate(channels)}},
    }


def window_iter(rec: Recording, window_s: float = 4.0, hop_s: float = 2.0):
    n = int(window_s * rec.fs)
    hop = int(hop_s * rec.fs)
    if rec.data.shape[1] < n:
        yield 0.0, rec.data
        return
    for start in range(0, rec.data.shape[1] - n + 1, hop):
        yield start / rec.fs, rec.data[:, start:start + n]


def analyze_recording(rec: Recording, window_s: float = 4.0, hop_s: float = 2.0, max_windows: int = 120) -> list[dict]:
    out = []
    for t0, w in window_iter(rec, window_s, hop_s):
        res = analyze_window(w, rec.fs, rec.channels)
        res["t0"] = round(t0, 2)
        out.append(res)
        if len(out) >= max_windows:
            break
    return out
