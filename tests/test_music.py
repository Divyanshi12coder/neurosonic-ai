import io
import wave

import pytest

from neurosonic_ml.music import mood as ml_mood, synth
from neurosonic_ml.music.explain import build_explanation
from neurosonic_ml.music.mood import TARGETS, fuse, mood_vector, plan_trajectory
from neurosonic_ml.music.profile import mood_to_profile, profile_to_prompt
from neurosonic_ml.music.providers import LocalSynthProvider, get_provider
from neurosonic_ml.music.recommend import rank, transition_playlist

CALM = dict(valence=.7, arousal=.2, calmness=.85, focus=.4, stress=.1)
EXCITED = dict(valence=.85, arousal=.88, calmness=.15, focus=.5, stress=.2)
STRESSED = dict(valence=.2, arousal=.85, calmness=.1, focus=.4, stress=.9)


def test_mood_vector_in_range():
    mv = mood_vector(EXCITED).to_dict()
    assert all(0 <= v <= 1 for v in mv.values()) and mv["energy"] > mood_vector(CALM).energy


def test_profile_calm_is_slow_and_sparse_vs_excited():
    calm, hype = mood_to_profile(CALM), mood_to_profile(EXCITED)
    assert calm["bpm"] < 80 < hype["bpm"]
    assert calm["rhythm_density"] < hype["rhythm_density"] and calm["percussion"] == "none"
    assert "soft pads" in calm["instrumentation"] and hype["percussion"] != "none"
    assert calm["scale"] in ("lydian", "major", "mixolydian") and mood_to_profile(STRESSED)["scale"] in ("aeolian", "phrygian", "dorian")


def test_profile_respects_preferences_and_prompt():
    p = mood_to_profile(CALM, ["piano"])
    assert p["timbre"] == "piano" and "felt piano" in p["instrumentation"]
    assert str(p["bpm"]) in profile_to_prompt(p)


def test_plan_match_mirrors_current():
    plan = plan_trajectory(STRESSED, "match", None, 1.0)
    assert plan["music"] == plan["current"] == plan["target"] and plan["shift"] == 0.0


def test_plan_shift_moves_toward_target_monotonically():
    plan = plan_trajectory(STRESSED, "shift", "calm", 1.0)
    arousal = [s["arousal"] for s in plan["trajectory"]]
    assert arousal == sorted(arousal, reverse=True) and len(arousal) == 4
    assert plan["trajectory"][0] == plan["current"] and plan["trajectory"][-1] == plan["target"]
    half = plan_trajectory(STRESSED, "shift", "calm", 0.5)
    assert abs(half["trajectory"][-1]["arousal"] - STRESSED["arousal"]) < abs(plan["trajectory"][-1]["arousal"] - STRESSED["arousal"])
    with pytest.raises(ValueError):
        plan_trajectory(STRESSED, "shift", "nonsense", 1.0)


def test_shift_to_calm_lowers_tempo_across_stages():
    plan = plan_trajectory(STRESSED, "shift", "calm", 1.0)
    bpms = [mood_to_profile(p)["bpm"] for p in plan["trajectory"]]
    assert bpms[0] > bpms[-1] + 20


def test_fusion_weights_sum_to_one_and_text_shifts_state():
    fused, w = fuse(CALM, 0.9, STRESSED, text_weight=0.3)
    assert abs(sum(w.values()) - 1) < 0.01 and fused["arousal"] > CALM["arousal"]
    only_text, w2 = fuse(None, 0.0, STRESSED)
    assert w2 == {"language": 1.0} and only_text["stress"] == pytest.approx(0.9, abs=0.01)
    with pytest.raises(ValueError):
        fuse(None, 0, None)


def test_recommend_prefers_matching_presets():
    top = rank(CALM, k=3)
    assert top[0]["point"]["arousal"] < 0.35
    hype = rank(EXCITED, k=3)
    assert hype[0]["point"]["arousal"] > 0.6


def test_recommend_personalisation():
    base = rank(CALM, k=24)
    target = base[5]["id"]
    boosted = rank(CALM, favorites={target}, ratings={target: 5}, k=24)
    assert [r["id"] for r in boosted].index(target) < [r["id"] for r in base].index(target)
    penalised = rank(CALM, ratings={base[0]["id"]: 1}, k=24)
    assert penalised[0]["id"] != base[0]["id"] or penalised[0]["score"] < base[0]["score"]
    piano = rank(CALM, prefs=["piano"], k=3)
    assert any("piano" in r["tags"] for r in piano)


def test_transition_playlist_has_distinct_stages():
    pl = transition_playlist(plan_trajectory(STRESSED, "shift", "calm", 1.0)["trajectory"])
    assert len(pl) == 4 and len({p["id"] for p in pl}) == 4 and [p["stage"] for p in pl] == [1, 2, 3, 4]


def test_synth_renders_valid_wav_of_requested_length():
    prof = mood_to_profile(CALM)
    audio = LocalSynthProvider().generate([prof], 6, seed=1, timbre="piano")
    with wave.open(io.BytesIO(audio.wav)) as w:
        assert w.getnchannels() == 1 and abs(w.getnframes() / w.getframerate() - 6) < 0.1
    x = synth.render([prof], duration=5, seed=2)
    assert 0.1 < abs(x).max() <= 1.0 and not (x != x).any()


def test_synth_is_deterministic_and_profile_sensitive():
    a, b = synth.render([mood_to_profile(CALM)], 4, seed=9), synth.render([mood_to_profile(CALM)], 4, seed=9)
    c = synth.render([mood_to_profile(EXCITED)], 4, seed=9)
    assert (a == b).all() and abs(a - c).mean() > 0.01


def test_provider_falls_back_without_key():
    assert get_provider("huggingface-musicgen", None).name == "local-synth"


def test_explanation_structure_and_caveats():
    plan = plan_trajectory(STRESSED, "shift", "calm", 1.0)
    emo = {**STRESSED, "confidence": .7, "label": "Stressed", "feature_importance": [
        {"feature": "rel_beta", "label": "Beta power", "value": .4, "z_score": 1.5, "importance": 1, "most_affects": "arousal", "direction": "raises"}]}
    ex = build_explanation(emo, plan, mood_to_profile(plan["music"]), rank(plan["music"])[0], {"eeg": 1.0})
    stages = [s["stage"] for s in ex["steps"]]
    assert stages[0] == "EEG signal" and "Estimated state" in stages and stages[-1] == "Reason"
    assert any("medical" in c.lower() for c in ex["caveats"])
    assert set(TARGETS) == {"calm", "focus", "energize", "refresh"} and ml_mood.clip01(2) == 1.0
