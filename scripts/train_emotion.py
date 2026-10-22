"""Train the emotion model and save it to models/.

  python scripts/train_emotion.py                          # synthetic baseline (what ships in models/)
  python scripts/train_emotion.py --dataset deap --path D:/data/DEAP/data_preprocessed_python --loso

DEAP is NOT bundled (licence). Request it at https://www.eecs.qmul.ac.uk/mmv/datasets/deap/ .
Only valence & arousal are real DEAP labels; calmness/stress are derived proxies and focus is constant (see dataset.py).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.metrics import r2_score  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

from neurosonic_ml.emotion.dataset import load_deap, make_synthetic_dataset  # noqa: E402
from neurosonic_ml.emotion.model import RandomForestEmotionModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["synthetic", "deap"], default="synthetic")
    ap.add_argument("--path", help="DEAP data_preprocessed_python directory")
    ap.add_argument("--n", type=int, default=1400, help="synthetic windows")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--loso", action="store_true", help="subject-independent grouped CV (DEAP only)")
    ap.add_argument("--max-subjects", type=int, default=None)
    a = ap.parse_args()

    if a.dataset == "deap":
        if not a.path:
            ap.error("--path is required for --dataset deap")
        X, Y, G = load_deap(a.path, max_subjects=a.max_subjects)
        if a.loso:
            folds = min(5, len(set(G)))
            r2 = {"valence": [], "arousal": []}
            for tr, te in GroupKFold(n_splits=folds).split(X, Y, G):
                est = RandomForestRegressor(n_estimators=160, min_samples_leaf=2, n_jobs=-1, random_state=a.seed).fit(X[tr], Y[tr])
                pred = est.predict(X[te])
                for i, d in enumerate(("valence", "arousal")):
                    r2[d].append(r2_score(Y[te][:, i], pred[:, i]))
            print("Subject-independent grouped CV R2 (mean +/- sd):")
            for d, v in r2.items():
                print(f"  {d}: {np.mean(v):.3f} +/- {np.std(v):.3f}")
        source = "DEAP"
    else:
        X, Y = make_synthetic_dataset(n=a.n, seed=a.seed)
        source = "synthetic"
    m = RandomForestEmotionModel()
    meta = m.fit(X, Y, data_source=source, seed=a.seed)
    path = m.save()
    print(json.dumps({k: meta[k] for k in ("data_source", "n_train", "n_test", "held_out_r2", "held_out_mae", "evaluation_note")}, indent=2))
    print("saved ->", path)


if __name__ == "__main__":
    main()
