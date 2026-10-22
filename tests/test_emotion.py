import pickle

import numpy as np

from neurosonic_ml.constants import CHANNELS, DIMENSIONS, FS
from neurosonic_ml.eeg.pipeline import analyze_window
from neurosonic_ml.emotion.dataset import DEAP_CHANNELS, load_deap
from neurosonic_ml.emotion.model import RandomForestEmotionModel, describe_state, get_default_model


def _predict(make_window, scenario, **kw):
    res = analyze_window(make_window(scenario, **kw), FS, CHANNELS)
    return get_default_model().predict(res["features"], res["quality"]["overall"])


def test_prediction_schema_and_ranges(make_window):
    p = _predict(make_window, "calm")
    for d in DIMENSIONS + ["confidence"]:
        assert 0.0 <= p[d] <= 1.0
    assert p["label"] and p["quadrant"]
    assert p["model"]["is_demo_baseline"] is True  # honest labelling of the synthetic baseline


def test_arousal_orders_calm_below_stressed_and_excited(make_window):
    calm, stressed, excited = (_predict(make_window, s) for s in ("calm", "stressed", "excited"))
    assert calm["arousal"] < 0.4 < stressed["arousal"] and excited["arousal"] > 0.6
    assert calm["calmness"] > stressed["calmness"]
    assert stressed["stress"] > calm["stress"]


def test_valence_orders_stressed_below_calm(make_window):
    seeds = range(5, 9)
    calm = np.mean([_predict(make_window, "calm", seed=s)["valence"] for s in seeds])
    stressed = np.mean([_predict(make_window, "stressed", seed=s)["valence"] for s in seeds])
    assert calm > stressed


def test_feature_importance_is_normalised_and_explained(make_window):
    fi = _predict(make_window, "stressed")["feature_importance"]
    assert fi[0]["importance"] == 1.0 and all(0 <= f["importance"] <= 1 for f in fi)
    assert {"feature", "label", "direction", "most_affects", "z_score"} <= set(fi[0])


def test_quality_lowers_confidence(make_window):
    res = analyze_window(make_window("calm"), FS, CHANNELS)
    m = get_default_model()
    assert m.predict(res["features"], 1.0)["confidence"] > m.predict(res["features"], 0.1)["confidence"]


def test_model_metadata_reports_heldout_metrics_with_caveat():
    info = get_default_model().info()
    assert info["held_out_r2"] and "NOT evidence" in info["evaluation_note"]


def test_describe_state_labels():
    assert "Calm" in describe_state(dict(valence=.7, arousal=.2, calmness=.8, focus=.4, stress=.1))[0]
    assert "Stressed" in describe_state(dict(valence=.2, arousal=.8, calmness=.1, focus=.4, stress=.8))[0]


def test_save_load_roundtrip(tmp_path):
    m = get_default_model()
    m.save(tmp_path)
    again = RandomForestEmotionModel.load(tmp_path)
    assert again.meta["feature_names"] == m.meta["feature_names"]


def test_deap_loader_on_fake_file(tmp_path):
    rng = np.random.RandomState(0)
    fake = {"data": rng.randn(2, 40, 128 * 11) * 10, "labels": np.array([[7, 3, 5, 5], [2, 8, 5, 5]], dtype=float)}
    with open(tmp_path / "s01.dat", "wb") as f:
        pickle.dump(fake, f)
    X, Y, G = load_deap(tmp_path)
    assert X.shape[1] == 13 and Y.shape[1] == 5 and len(X) == len(Y) == len(G) > 0
    assert Y[0, 0] == (7 - 1) / 8 and Y[0, 1] == (3 - 1) / 8
    assert len(DEAP_CHANNELS) == 32
