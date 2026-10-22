"""EEG feature extraction: Welch PSD band powers, ratios, entropy, Hjorth and temporal statistics."""
from __future__ import annotations

import numpy as np
from scipy import signal, stats

from ..constants import BANDS

# Order matters: this is the model input vector.
FEATURE_NAMES = [
    "rel_delta", "rel_theta", "rel_alpha", "rel_beta", "rel_gamma",
    "theta_beta_ratio", "alpha_beta_ratio", "engagement_index",
    "frontal_alpha_asymmetry", "spectral_entropy", "dominant_frequency",
    "hjorth_mobility", "hjorth_complexity",
]
FEATURE_LABELS = {
    "rel_delta": "Delta power", "rel_theta": "Theta power", "rel_alpha": "Alpha power",
    "rel_beta": "Beta power", "rel_gamma": "Gamma power",
    "theta_beta_ratio": "Theta/Beta ratio", "alpha_beta_ratio": "Alpha/Beta ratio",
    "engagement_index": "Engagement index β/(α+θ)",
    "frontal_alpha_asymmetry": "Frontal alpha asymmetry",
    "spectral_entropy": "Spectral entropy", "dominant_frequency": "Dominant frequency",
    "hjorth_mobility": "Hjorth mobility", "hjorth_complexity": "Hjorth complexity",
}
ASYM_PAIRS = [("AF7", "AF8"), ("AF3", "AF4"), ("F3", "F4"), ("Fp1", "Fp2")]


def _band_power(freqs: np.ndarray, psd: np.ndarray, lo: float, hi: float) -> np.ndarray:
    m = (freqs >= lo) & (freqs < hi)
    if m.sum() < 2:
        return np.zeros(psd.shape[:-1])
    return np.trapezoid(psd[..., m], freqs[m], axis=-1)


def _hjorth(x: np.ndarray) -> tuple[float, float, float]:
    dx = np.diff(x)
    ddx = np.diff(dx)
    var0, var1, var2 = np.var(x), np.var(dx), np.var(ddx)
    mobility = np.sqrt(var1 / (var0 + 1e-12))
    complexity = np.sqrt(var2 / (var1 + 1e-12)) / (mobility + 1e-12)
    return float(var0), float(mobility), float(complexity)


def extract_features(filtered: np.ndarray, fs: float, channel_names: list[str]) -> dict:
    """filtered: (channels, samples). Returns a rich feature dict (JSON-serialisable)."""
    n = filtered.shape[1]
    nperseg = int(min(n, 2 * fs))
    freqs, psd = signal.welch(filtered, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, axis=-1)

    nyq_cap = fs * 0.45
    bands = {b: (lo, min(hi, nyq_cap)) for b, (lo, hi) in BANDS.items() if lo < nyq_cap}
    abs_ch = {b: _band_power(freqs, psd, lo, hi) for b, (lo, hi) in bands.items()}  # per channel
    for b in BANDS:
        abs_ch.setdefault(b, np.zeros(filtered.shape[0]))
    total_ch = sum(abs_ch.values()) + 1e-12
    rel_ch = {b: abs_ch[b] / total_ch for b in BANDS}

    abs_mean = {b: float(abs_ch[b].mean()) for b in BANDS}
    total = sum(abs_mean.values()) + 1e-12
    rel = {b: abs_mean[b] / total for b in BANDS}

    eps = 1e-9
    theta_beta = rel["theta"] / (rel["beta"] + eps)
    alpha_beta = rel["alpha"] / (rel["beta"] + eps)
    engagement = rel["beta"] / (rel["alpha"] + rel["theta"] + eps)

    asym = 0.0
    names = list(channel_names)
    for left, right in ASYM_PAIRS:
        if left in names and right in names:
            li, ri = names.index(left), names.index(right)
            asym = float(np.log(abs_ch["alpha"][ri] + eps) - np.log(abs_ch["alpha"][li] + eps))
            break

    mean_psd = psd.mean(axis=0)
    m = (freqs >= 1) & (freqs <= min(45, nyq_cap))
    p = mean_psd[m] / (mean_psd[m].sum() + eps)
    entropy = float(-(p * np.log(p + eps)).sum() / np.log(len(p))) if len(p) > 1 else 0.0
    dm = (freqs >= 4) & (freqs <= 30)
    dominant = float(freqs[dm][np.argmax(mean_psd[dm])]) if dm.any() else 0.0

    hj = [_hjorth(ch) for ch in filtered]
    mobility = float(np.mean([h[1] for h in hj]))
    complexity = float(np.mean([h[2] for h in hj]))
    flat = filtered.reshape(-1)

    vec = {
        "rel_delta": rel["delta"], "rel_theta": rel["theta"], "rel_alpha": rel["alpha"],
        "rel_beta": rel["beta"], "rel_gamma": rel["gamma"],
        "theta_beta_ratio": theta_beta, "alpha_beta_ratio": alpha_beta,
        "engagement_index": engagement, "frontal_alpha_asymmetry": asym,
        "spectral_entropy": entropy, "dominant_frequency": dominant,
        "hjorth_mobility": mobility, "hjorth_complexity": complexity,
    }
    plot_m = (freqs >= 1) & (freqs <= min(45, nyq_cap))
    step = max(1, int(plot_m.sum() // 90))
    return {
        "band_power": {b: round(abs_mean[b], 4) for b in BANDS},
        "relative_band_power": {b: round(rel[b], 4) for b in BANDS},
        "per_channel_relative": {
            ch: {b: round(float(rel_ch[b][i]), 4) for b in BANDS} for i, ch in enumerate(names)
        },
        "ratios": {"theta_beta": round(theta_beta, 4), "alpha_beta": round(alpha_beta, 4), "engagement": round(engagement, 4)},
        "frontal_alpha_asymmetry": round(asym, 4),
        "dominant_frequency": round(dominant, 3),
        "spectral_entropy": round(entropy, 4),
        "signal_variance": round(float(np.var(flat)), 4),
        "temporal": {
            "mean": round(float(flat.mean()), 5), "std": round(float(flat.std()), 4),
            "skewness": round(float(stats.skew(flat)), 4), "kurtosis": round(float(stats.kurtosis(flat)), 4),
            "line_length": round(float(np.mean(np.abs(np.diff(filtered, axis=1)))), 4),
            "zero_crossing_rate": round(float(np.mean(np.diff(np.signbit(filtered), axis=1))), 4),
            "hjorth_mobility": round(mobility, 4), "hjorth_complexity": round(complexity, 4),
        },
        "psd": {
            "freqs": [round(float(f), 2) for f in freqs[plot_m][::step]],
            "power": [round(float(v), 4) for v in mean_psd[plot_m][::step]],
        },
        "vector": {k: round(float(v), 6) for k, v in vec.items()},
    }


def feature_vector(features_or_vector: dict) -> np.ndarray:
    v = features_or_vector.get("vector", features_or_vector)
    missing = [k for k in FEATURE_NAMES if k not in v]
    if missing:
        raise ValueError(f"missing features: {missing}")
    return np.array([float(v[k]) for k in FEATURE_NAMES])
