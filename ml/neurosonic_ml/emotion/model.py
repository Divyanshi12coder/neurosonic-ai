"""Emotion estimation from EEG features.

`EmotionModel` is the provider interface; `RandomForestEmotionModel` is the bundled baseline.
The default baseline is trained on SYNTHETIC EEG (see dataset.py) and is a pipeline
demonstration, not a validated affective-computing model.
"""
from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

from ..constants import DIMENSIONS
from ..eeg.features import FEATURE_LABELS, FEATURE_NAMES, feature_vector

MODEL_DIR = Path(__file__).resolve().parents[3] / "models"


def _clip01(x):
    return float(min(1.0, max(0.0, x)))


def describe_state(p: dict[str, float]) -> tuple[str, str]:
    """Human-readable label + valence/arousal quadrant."""
    v, a = p["valence"], p["arousal"]
    quad = ("Excited / Energised" if v >= 0.5 else "Tense / Stressed") if a >= 0.5 else (
        "Calm / Content" if v >= 0.5 else "Low / Melancholic")
    parts = []
    if p["calmness"] >= 0.6 and a < 0.5:
        parts.append("Calm")
    if p["stress"] >= 0.6:
        parts.append("Stressed")
    if p["focus"] >= 0.65:
        parts.append("Focused")
    elif p["focus"] <= 0.25 and a < 0.35:
        parts.append("Drowsy")
    if not parts:
        parts.append(quad.split(" / ")[0])
    return " · ".join(parts), quad


class EmotionModel(ABC):
    name: str

    @abstractmethod
    def predict(self, features: dict) -> dict: ...

    @abstractmethod
    def info(self) -> dict: ...


class RandomForestEmotionModel(EmotionModel):
    name = "random-forest-baseline"

    def __init__(self, estimator: RandomForestRegressor | None = None, meta: dict | None = None):
        self.est = estimator
        self.meta = meta or {}

    # ---------- training ----------
    def fit(self, X: np.ndarray, Y: np.ndarray, data_source: str, seed: int = 0) -> dict:
        Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=seed)
        self.est = RandomForestRegressor(n_estimators=160, min_samples_leaf=2, n_jobs=-1, random_state=seed)
        self.est.fit(Xtr, Ytr)
        pred = self.est.predict(Xte)
        r2 = {d: round(float(r2_score(Yte[:, i], pred[:, i])), 3) for i, d in enumerate(DIMENSIONS)}
        mae = {d: round(float(np.mean(np.abs(Yte[:, i] - pred[:, i]))), 3) for i, d in enumerate(DIMENSIONS)}
        self.meta = {
            "name": self.name,
            "data_source": data_source,
            "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
            "feature_names": FEATURE_NAMES,
            "feature_means": X.mean(axis=0).tolist(),
            "feature_stds": (X.std(axis=0) + 1e-9).tolist(),
            "held_out_r2": r2, "held_out_mae": mae,
            "evaluation_note": (
                "Held-out split of the SAME data distribution. For synthetic data this only shows the model can "
                "invert the simulator; it is NOT evidence of real-world EEG emotion accuracy."
                if data_source == "synthetic" else
                "Random window-level split; windows from the same trial/subject can leak across splits. "
                "Use subject-independent cross-validation (scripts/train_emotion.py --loso) for honest estimates."
            ),
        }
        return self.meta

    def save(self, directory: Path = MODEL_DIR) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.est, directory / "emotion_rf.joblib")
        (directory / "emotion_rf.meta.json").write_text(json.dumps(self.meta, indent=2))
        return directory / "emotion_rf.joblib"

    @classmethod
    def load(cls, directory: Path = MODEL_DIR) -> "RandomForestEmotionModel":
        est = joblib.load(directory / "emotion_rf.joblib")
        meta = json.loads((directory / "emotion_rf.meta.json").read_text())
        return cls(est, meta)

    # ---------- inference ----------
    def predict(self, features: dict, quality: float = 1.0) -> dict:
        x = feature_vector(features).reshape(1, -1)
        tree_preds = np.stack([t.predict(x)[0] for t in self.est.estimators_])  # (trees, dims)
        mean = tree_preds.mean(axis=0)
        spread = tree_preds.std(axis=0)
        probs = {d: _clip01(mean[i]) for i, d in enumerate(DIMENSIONS)}
        # Confidence: agreement between trees, discounted by signal quality. A heuristic, not a calibrated probability.
        agreement = 1.0 - min(1.0, float(spread.mean()) * 3.5)
        confidence = _clip01(agreement * (0.4 + 0.6 * quality))
        label, quadrant = describe_state(probs)
        return {
            **{d: round(v, 4) for d, v in probs.items()},
            "confidence": round(confidence, 3),
            "label": label, "quadrant": quadrant,
            "feature_importance": self._explain(x, mean),
            "model": self.public_info(),
        }

    def _explain(self, x: np.ndarray, base_pred: np.ndarray) -> list[dict]:
        """Local, perturbation-based attribution: replace each feature by its training mean, measure output change."""
        means = np.array(self.meta["feature_means"])
        stds = np.array(self.meta["feature_stds"])
        glob = dict(zip(FEATURE_NAMES, self.est.feature_importances_))
        deltas = []
        for i in range(x.shape[1]):
            x2 = x.copy()
            x2[0, i] = means[i]
            p2 = self.est.predict(x2)[0]
            deltas.append(base_pred - p2)  # signed effect of the feature on each dimension
        deltas = np.array(deltas)
        mag = np.abs(deltas).sum(axis=1)
        top = mag.max() + 1e-12
        rows = []
        for i, name in enumerate(FEATURE_NAMES):
            dom = int(np.argmax(np.abs(deltas[i])))
            rows.append({
                "feature": name, "label": FEATURE_LABELS[name],
                "value": round(float(x[0, i]), 4),
                "z_score": round(float((x[0, i] - means[i]) / stds[i]), 2),
                "importance": round(float(mag[i] / top), 3),
                "global_importance": round(float(glob[name]), 3),
                "most_affects": DIMENSIONS[dom],
                "direction": "raises" if deltas[i][dom] > 0 else "lowers",
            })
        return sorted(rows, key=lambda r: -r["importance"])

    def public_info(self) -> dict:
        return {
            "name": self.name,
            "data_source": self.meta.get("data_source", "unknown"),
            "is_demo_baseline": self.meta.get("data_source") == "synthetic",
            "label": ("Synthetic-data baseline (pipeline demonstration)" if self.meta.get("data_source") == "synthetic"
                      else f"Trained on {self.meta.get('data_source')}"),
        }

    def info(self) -> dict:
        return {**self.public_info(), "held_out_r2": self.meta.get("held_out_r2"),
                "held_out_mae": self.meta.get("held_out_mae"), "n_train": self.meta.get("n_train"),
                "evaluation_note": self.meta.get("evaluation_note"), "dimensions": DIMENSIONS}


_lock = threading.Lock()
_default: RandomForestEmotionModel | None = None


def train_default(n: int = 1400, seed: int = 0) -> RandomForestEmotionModel:
    from .dataset import make_synthetic_dataset
    X, Y = make_synthetic_dataset(n=n, seed=seed)
    m = RandomForestEmotionModel()
    m.fit(X, Y, data_source="synthetic", seed=seed)
    m.save()
    return m


def get_default_model() -> RandomForestEmotionModel:
    """Load the saved model, training the synthetic baseline on first use if none exists."""
    global _default
    with _lock:
        if _default is None:
            try:
                _default = RandomForestEmotionModel.load()
            except Exception:  # noqa: BLE001 - missing or incompatible artefact
                _default = train_default()
        return _default
