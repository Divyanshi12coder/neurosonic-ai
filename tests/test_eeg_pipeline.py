import json

import numpy as np
import pytest

from neurosonic_ml.constants import BANDS, CHANNELS, FS
from neurosonic_ml.eeg.features import FEATURE_NAMES, extract_features, feature_vector
from neurosonic_ml.eeg.io import EEGFormatError, parse_csv, parse_json, parse_upload
from neurosonic_ml.eeg.pipeline import analyze_recording, analyze_window
from neurosonic_ml.eeg.preprocessing import preprocess, signal_quality
from neurosonic_ml.eeg.synthetic import generate_window, scenario_latent


@pytest.mark.parametrize("freq,band", [(2.0, "delta"), (6.0, "theta"), (10.0, "alpha"), (20.0, "beta"), (38.0, "gamma")])
def test_dominant_band_matches_injected_sine(sine_eeg, freq, band):
    feats = extract_features(preprocess(sine_eeg(freq), FS), FS, CHANNELS)
    rel = feats["relative_band_power"]
    assert max(rel, key=rel.get) == band
    assert abs(sum(rel.values()) - 1.0) < 0.01


def test_dominant_frequency_close_to_injected(sine_eeg):
    feats = extract_features(preprocess(sine_eeg(10.0), FS), FS, CHANNELS)
    assert abs(feats["dominant_frequency"] - 10.0) < 1.0


def test_notch_filter_removes_mains(sine_eeg):
    raw = sine_eeg(10.0) + 30 * np.sin(2 * np.pi * 50 * np.arange(4 * FS) / FS)
    f = preprocess(raw, FS, notch_hz=50.0)
    spec = np.abs(np.fft.rfft(f[0])) ** 2
    freqs = np.fft.rfftfreq(f.shape[1], 1 / FS)
    assert spec[np.argmin(abs(freqs - 50))] < 0.01 * spec[np.argmin(abs(freqs - 10))]


def test_feature_vector_complete_and_finite(make_window):
    res = analyze_window(make_window(), FS, CHANNELS)
    vec = feature_vector(res["features"])
    assert len(vec) == len(FEATURE_NAMES) and np.isfinite(vec).all()
    for key in ("band_power", "relative_band_power", "ratios", "spectral_entropy", "signal_variance", "temporal", "psd"):
        assert key in res["features"]
    assert set(res["features"]["band_power"]) == set(BANDS)


def test_spectral_entropy_higher_for_noise_than_sine(sine_eeg):
    noise = np.random.RandomState(1).randn(4, 4 * FS) * 10
    e_noise = extract_features(preprocess(noise, FS), FS, CHANNELS)["spectral_entropy"]
    e_sine = extract_features(preprocess(sine_eeg(10.0), FS), FS, CHANNELS)["spectral_entropy"]
    assert e_noise > e_sine


def test_frontal_alpha_asymmetry_sign():
    # More alpha on the right (AF8) than the left (AF7) -> positive asymmetry (ln R - ln L)
    t = np.arange(4 * FS) / FS
    x = np.stack([np.sin(2 * np.pi * 10 * t) * a for a in (5, 5, 20, 5)])  # TP9, AF7, AF8, TP10
    assert extract_features(preprocess(x, FS), FS, CHANNELS)["frontal_alpha_asymmetry"] > 0.5


def test_quality_flags_flatline_and_artifacts(make_window):
    raw = make_window()
    good = signal_quality(raw, preprocess(raw, FS), FS)
    assert good["label"] in ("good", "fair")
    flat = np.zeros_like(raw)
    assert signal_quality(flat, flat, FS)["overall"] == 0.0
    noisy = raw + 400 * np.random.RandomState(0).randn(*raw.shape)
    assert signal_quality(noisy, preprocess(noisy, FS), FS)["overall"] < good["overall"]


def test_synthetic_stream_is_phase_continuous():
    lat = scenario_latent("calm")
    a = generate_window(lat, t0=0.0, duration=2.0, seed=3, artifacts=False)
    b = generate_window(lat, t0=1.0, duration=2.0, seed=3, artifacts=False)
    # overlapping second (a[1:2s] vs b[0:1s]) is the same oscillation up to the noise term
    assert np.corrcoef(a[1, FS:], b[1, :FS])[0, 1] > 0.9


def test_scenarios_have_expected_spectral_contrast(make_window):
    def rel(s):
        return analyze_window(make_window(s), FS, CHANNELS)["features"]["relative_band_power"]
    assert rel("calm")["alpha"] > rel("stressed")["alpha"]
    assert rel("stressed")["beta"] > rel("calm")["beta"]


def test_csv_parsing_with_timestamps():
    n = FS * 3
    rows = ["time,TP9,AF7,AF8,TP10"] + [f"{i / FS},{i % 7},{i % 5},{i % 3},{i % 11}" for i in range(n)]
    rec = parse_csv("\n".join(rows))
    assert rec.channels == ["TP9", "AF7", "AF8", "TP10"] and abs(rec.fs - FS) < 1 and rec.data.shape[0] == 4


def test_csv_without_fs_is_rejected():
    with pytest.raises(EEGFormatError):
        parse_csv("a,b\n" + "\n".join("1,2" for _ in range(1000)))


def test_json_parsing_and_validation():
    data = {"fs": 128, "data": {"Fp1": list(np.sin(np.arange(400) / 5)), "Fp2": list(np.cos(np.arange(400) / 5))}}
    rec = parse_json(json.dumps(data))
    assert rec.channels == ["Fp1", "Fp2"] and rec.fs == 128
    with pytest.raises(EEGFormatError):
        parse_json(json.dumps({"fs": 128, "data": {"a": [1, 2, 3]}}))  # too short
    with pytest.raises(EEGFormatError):
        parse_json("not json")
    with pytest.raises(EEGFormatError):
        parse_upload("x.exe", b"")


def test_recording_windows(make_window):
    from neurosonic_ml.eeg.io import Recording
    raw = np.concatenate([make_window(t0=i * 4.0) for i in range(3)], axis=1)
    wins = analyze_recording(Recording(FS, CHANNELS, raw), 4.0, 2.0)
    assert len(wins) == 5 and wins[1]["t0"] == 2.0
