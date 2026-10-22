"""EEG preprocessing: detrending, notch + band-pass filtering, normalisation, quality scoring."""
from __future__ import annotations

import numpy as np
from scipy import signal


def preprocess(x: np.ndarray, fs: float, notch_hz: float | None = 50.0, band: tuple[float, float] = (0.5, 45.0)) -> np.ndarray:
    """x: (channels, samples) in µV. Returns filtered copy."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        raise ValueError("EEG array must be 2-D (channels, samples)")
    nyq = fs / 2.0
    x = signal.detrend(x, axis=1, type="linear")
    if notch_hz and notch_hz < nyq * 0.95:
        b, a = signal.iirnotch(notch_hz, Q=30.0, fs=fs)
        x = signal.filtfilt(b, a, x, axis=1)
    lo, hi = band
    hi = min(hi, nyq * 0.9)
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=1)


def zscore(x: np.ndarray) -> np.ndarray:
    return (x - x.mean(axis=1, keepdims=True)) / (x.std(axis=1, keepdims=True) + 1e-9)


def signal_quality(raw: np.ndarray, filtered: np.ndarray, fs: float) -> dict:
    """Heuristic per-channel quality 0..1: penalises flat lines, large artifacts and extreme kurtosis."""
    per = []
    for r, f in zip(raw, filtered):
        std = float(np.std(f))
        if std < 0.05:
            per.append(0.0)
            continue
        artifact_frac = float(np.mean(np.abs(f) > 100.0))
        k = float(((f - f.mean()) ** 4).mean() / (std**4 + 1e-12))  # ~3 for gaussian
        s = 1.0 - min(1.0, artifact_frac * 8) - min(0.4, max(0.0, (k - 5) * 0.05))
        per.append(max(0.0, min(1.0, s)))
    overall = float(np.mean(per)) if per else 0.0
    return {
        "overall": round(overall, 3),
        "per_channel": [round(p, 3) for p in per],
        "label": "good" if overall >= 0.75 else "fair" if overall >= 0.45 else "poor",
    }
