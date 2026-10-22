"""Synthetic EEG generator used by Demo Mode and for training the baseline model.

The generator is driven by a *latent mental state* (valence, arousal, focus, stress,
calm). The latent state sets band amplitudes following broad, well-known tendencies
(e.g. more alpha when relaxed, more beta when aroused, frontal alpha asymmetry related
to valence). The resulting raw signal is then pushed through exactly the same
preprocessing/feature pipeline as uploaded recordings.

This is a *simulation*: it is useful for demonstrating and testing the pipeline, not
evidence that real EEG behaves this way for any individual.
"""
from __future__ import annotations

import numpy as np

from ..constants import BANDS, CHANNELS, FS

SCENARIOS: dict[str, dict[str, float]] = {
    "calm": dict(valence=0.72, arousal=0.24, focus=0.45, stress=0.14, calm=0.84),
    "focused": dict(valence=0.62, arousal=0.55, focus=0.86, stress=0.24, calm=0.50),
    "stressed": dict(valence=0.24, arousal=0.82, focus=0.38, stress=0.86, calm=0.14),
    "excited": dict(valence=0.82, arousal=0.86, focus=0.50, stress=0.30, calm=0.18),
    "drowsy": dict(valence=0.45, arousal=0.10, focus=0.14, stress=0.18, calm=0.52),
    "melancholic": dict(valence=0.20, arousal=0.24, focus=0.30, stress=0.42, calm=0.40),
}
AUTO_ORDER = ["calm", "focused", "stressed", "excited", "drowsy", "melancholic"]
AUTO_DWELL_S = 24.0
AUTO_FADE_S = 8.0


def _smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def scenario_latent(name: str, t: float = 0.0) -> dict[str, float]:
    """Latent state for a scenario at absolute time `t` seconds. `auto` cycles through states."""
    if name != "auto":
        if name not in SCENARIOS:
            raise ValueError(f"unknown scenario '{name}'")
        return dict(SCENARIOS[name])
    n = len(AUTO_ORDER)
    idx = int(t // AUTO_DWELL_S) % n
    frac = (t % AUTO_DWELL_S) / AUTO_DWELL_S
    fade_start = 1 - AUTO_FADE_S / AUTO_DWELL_S
    cur, nxt = SCENARIOS[AUTO_ORDER[idx]], SCENARIOS[AUTO_ORDER[(idx + 1) % n]]
    w = _smoothstep((frac - fade_start) / (1 - fade_start)) if frac > fade_start else 0.0
    return {k: cur[k] * (1 - w) + nxt[k] * w for k in cur}


def current_scenario_name(name: str, t: float) -> str:
    if name != "auto":
        return name
    return AUTO_ORDER[int(t // AUTO_DWELL_S) % len(AUTO_ORDER)]


def band_amplitudes(latent: dict[str, float], channel: str) -> dict[str, float]:
    """Sinusoid amplitude (µV) per band for a channel, as a function of latent state."""
    a, c, f, s, v = latent["arousal"], latent["calm"], latent["focus"], latent["stress"], latent["valence"]
    amps = {
        "delta": 9.0 * (0.5 + 0.9 * (1 - a)),
        "theta": 7.0 * (0.6 + 0.9 * (1 - a) + 0.35 * f),
        "alpha": 13.0 * (0.45 + 0.9 * c + 0.5 * (1 - a)),
        "beta": 4.5 * (0.55 + 1.15 * a + 0.9 * s + 0.5 * f),
        "gamma": 1.4 * (0.5 + 0.9 * a + 0.6 * s),
    }
    # Frontal alpha asymmetry: more positive valence -> relatively less left (AF7) alpha.
    skew = 0.30 * (v - 0.5) * 2
    if channel == "AF7":
        amps["alpha"] *= 1 - skew
    elif channel == "AF8":
        amps["alpha"] *= 1 + skew
    if channel.startswith("TP"):  # temporal sites: weaker beta/gamma, a bit more alpha
        amps["beta"] *= 0.7
        amps["gamma"] *= 0.6
        amps["alpha"] *= 1.1
    return amps


def _pink_noise(rng: np.random.RandomState, n: int) -> np.ndarray:
    white = rng.randn(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = freqs[1] if n > 1 else 1.0
    spec /= np.sqrt(freqs)
    pink = np.fft.irfft(spec, n)
    return pink / (np.std(pink) + 1e-9)


def _hash01(seed: int, k: int, salt: int) -> float:
    return float(np.random.RandomState((seed * 7919 + k * 104729 + salt * 13) % (2**31 - 1)).rand())


def generate_window(
    latent: dict[str, float],
    t0: float = 0.0,
    duration: float = 4.0,
    fs: int = FS,
    seed: int = 7,
    channels: list[str] | None = None,
    artifacts: bool = True,
    gain: float = 1.0,
) -> np.ndarray:
    """Return array (n_channels, n_samples) in µV. Phase-continuous across calls with increasing t0."""
    channels = channels or CHANNELS
    n = int(round(duration * fs))
    t = t0 + np.arange(n) / fs
    rng = np.random.RandomState((seed * 100003 + int(t0 * 10)) % (2**31 - 1))
    out = np.zeros((len(channels), n))
    for ci, ch in enumerate(channels):
        amps = band_amplitudes(latent, ch)
        sig = np.zeros(n)
        for bi, (band, (lo, hi)) in enumerate(BANDS.items()):
            for k in range(3):
                frs = np.random.RandomState(seed * 31 + ci * 97 + bi * 7 + k)
                freq = lo + (hi - lo) * (0.1 + 0.8 * frs.rand())
                phase = 2 * np.pi * frs.rand()
                mod = 1 + 0.25 * np.sin(2 * np.pi * 0.1 * t + 2 * np.pi * frs.rand())
                sig += amps[band] / np.sqrt(3) * mod * np.sin(2 * np.pi * freq * t + phase)
        sig += 3.0 * _pink_noise(rng, n) + 1.5 * rng.randn(n)
        if artifacts and ch in ("AF7", "AF8"):
            for k in range(int(t0 // 5) - 1, int((t0 + duration) // 5) + 1):
                if _hash01(seed, k, 1) < 0.45:  # blink roughly every ~10 s
                    te = k * 5 + 4 * _hash01(seed, k, 2)
                    sig += 55.0 * np.exp(-0.5 * ((t - te) / 0.12) ** 2)
        out[ci] = sig * gain
    return out
