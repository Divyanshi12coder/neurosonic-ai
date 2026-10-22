"""Training data for the emotion baseline.

* `make_synthetic_dataset` – windows from the synthetic EEG generator (default, bundled).
* `load_deap` – loader for the public DEAP dataset (preprocessed python version, `sXX.dat`).
  DEAP cannot be redistributed; see docs/ai-models.md for how to obtain it.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from ..constants import CHANNELS, DIMENSIONS, FS
from ..eeg.features import FEATURE_NAMES, extract_features
from ..eeg.preprocessing import preprocess
from ..eeg.synthetic import generate_window

DEAP_CHANNELS = [
    "Fp1", "AF3", "F3", "F7", "FC5", "FC1", "C3", "T7", "CP5", "CP1", "P3", "P7", "PO3", "O1", "Oz", "Pz",
    "Fp2", "AF4", "Fz", "F4", "F8", "FC6", "FC2", "Cz", "C4", "T8", "CP6", "CP2", "P4", "P8", "PO4", "O2",
]


def sample_latent(rng: np.random.RandomState) -> dict[str, float]:
    v, a, f = rng.rand(), rng.rand(), rng.rand()
    stress = float(np.clip(0.5 * (1 - v) + 0.5 * a + rng.randn() * 0.12, 0, 1))
    calm = float(np.clip(1 - 0.7 * a - 0.3 * stress + rng.randn() * 0.08, 0, 1))
    return dict(valence=float(v), arousal=float(a), focus=float(f), stress=stress, calm=calm)


def make_synthetic_dataset(n: int = 1400, seed: int = 0, window_s: float = 4.0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.RandomState(seed)
    X, Y = [], []
    for i in range(n):
        lat = sample_latent(rng)
        raw = generate_window(lat, t0=float(rng.rand() * 600), duration=window_s, fs=FS, seed=int(rng.randint(1, 10**6)),
                              gain=float(0.75 + 0.5 * rng.rand()))
        feats = extract_features(preprocess(raw, FS), FS, CHANNELS)["vector"]
        X.append([feats[k] for k in FEATURE_NAMES])
        Y.append([lat["valence"], lat["arousal"], lat["calm"], lat["focus"], lat["stress"]])
    return np.array(X), np.array(Y)


def load_deap(directory: str | Path, fs: float = 128.0, window_s: float = 4.0, max_subjects: int | None = None):
    """Load DEAP `data_preprocessed_python/sXX.dat`. Returns X, Y, subject_ids (for subject-independent CV). Only valence & arousal are real labels (1-9 -> 0..1).

    calmness/focus/stress are NOT measured in DEAP; they are filled with documented proxies so the
    5-dim model head can be trained: calm=1-arousal, stress=(arousal+(1-valence))/2, focus=0.5.
    """
    files = sorted(Path(directory).glob("s*.dat"))
    if not files:
        raise FileNotFoundError(f"no sXX.dat files found in {directory}")
    X, Y, G = [], [], []
    n = int(window_s * fs)
    for subj, fp in enumerate(files[:max_subjects]):
        with open(fp, "rb") as fh:
            d = pickle.load(fh, encoding="latin1")  # noqa: S301 - trusted local research file
        data, labels = np.asarray(d["data"]), np.asarray(d["labels"])
        for trial in range(data.shape[0]):
            eeg = data[trial, :32, int(3 * fs):]  # drop the 3 s pre-trial baseline
            val, aro = (labels[trial, 0] - 1) / 8.0, (labels[trial, 1] - 1) / 8.0
            for s in range(0, eeg.shape[1] - n + 1, n):
                filt = preprocess(eeg[:, s:s + n], fs, notch_hz=50.0)
                v = extract_features(filt, fs, DEAP_CHANNELS)["vector"]
                X.append([v[k] for k in FEATURE_NAMES])
                Y.append([val, aro, 1 - aro, 0.5, (aro + (1 - val)) / 2])
                G.append(subj)
    return np.array(X), np.array(Y), np.array(G)


assert len(DIMENSIONS) == 5
