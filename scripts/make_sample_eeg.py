"""Write sample EEG recordings (synthetic!) to data/sample/ for trying the Upload flow."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

import numpy as np  # noqa: E402

from neurosonic_ml.constants import CHANNELS, FS  # noqa: E402
from neurosonic_ml.eeg.synthetic import generate_window, scenario_latent  # noqa: E402

out = ROOT / "data" / "sample"
out.mkdir(parents=True, exist_ok=True)
for name in ("calm", "focused", "stressed"):
    parts = [generate_window(scenario_latent(name), t0=i * 4.0, duration=4.0, seed=11) for i in range(3)]
    x = np.concatenate(parts, axis=1)
    t = np.arange(x.shape[1]) / FS
    with open(out / f"synthetic_{name}.csv", "w") as f:
        f.write("time," + ",".join(CHANNELS) + "\n")
        for i in range(x.shape[1]):
            f.write(f"{t[i]:.5f}," + ",".join(f"{v:.3f}" for v in x[:, i]) + "\n")
    print("wrote", out / f"synthetic_{name}.csv")
x = generate_window(scenario_latent("calm"), 0, 8.0, seed=3)
(out / "synthetic_calm.json").write_text(json.dumps({"fs": FS, "data": {c: np.round(x[i], 2).tolist() for i, c in enumerate(CHANNELS)}}))
print("wrote synthetic_calm.json")
