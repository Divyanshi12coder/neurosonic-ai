"""Test configuration: isolated SQLite DB + data dir, and import paths for backend/ and ml/."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_tmp = Path(tempfile.mkdtemp(prefix="neurosonic-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(_tmp)
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["LLM_API_KEY"] = ""
for p in (ROOT / "ml", ROOT / "backend"):
    sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from neurosonic_ml.constants import CHANNELS, FS  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/auth/demo")
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def make_window():
    from neurosonic_ml.eeg.synthetic import generate_window, scenario_latent

    def _make(scenario="calm", t0=0.0, seed=5, duration=4.0):
        return generate_window(scenario_latent(scenario), t0=t0, duration=duration, fs=FS, seed=seed)
    return _make


@pytest.fixture(scope="session")
def sine_eeg():
    def _make(freq, amp=20.0, seconds=4, fs=FS, channels=CHANNELS):
        t = np.arange(int(seconds * fs)) / fs
        rng = np.random.RandomState(0)
        return np.stack([amp * np.sin(2 * np.pi * freq * t) + 0.5 * rng.randn(len(t)) for _ in channels])
    return _make
