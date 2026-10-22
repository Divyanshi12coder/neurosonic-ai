"""'Why this music?' explanation builder: EEG signal -> estimated state -> strategy -> reason."""
from __future__ import annotations

from ..constants import DISCLAIMER

_BAND_PHRASE = {
    "rel_alpha": ("Alpha activity", "relaxed wakefulness is often associated with stronger alpha"),
    "rel_beta": ("Beta activity", "higher beta is commonly linked with alertness, active thinking or tension"),
    "rel_theta": ("Theta activity", "theta tends to rise with drowsiness and internal focus"),
    "rel_delta": ("Delta activity", "delta is dominant in deep sleep; small amounts occur awake"),
    "rel_gamma": ("Gamma activity", "gamma is linked with high-frequency processing but is easily contaminated by muscle noise"),
}


def _level(z: float) -> str:
    return "elevated" if z > 0.6 else "reduced" if z < -0.6 else "near typical"


def build_explanation(emotion: dict | None, plan: dict, profile: dict, preset: dict | None, weights: dict | None,
                      text_analysis: dict | None = None, quality_label: str | None = None) -> dict:
    steps = []
    features = (emotion or {}).get("feature_importance", [])
    if emotion:
        band_feats = [f for f in features if f["feature"] in _BAND_PHRASE]
        top = band_feats[0] if band_feats else (features[0] if features else None)
        if top:
            name, why = _BAND_PHRASE.get(top["feature"], (top["label"], "feature with highest influence"))
            steps.append({"stage": "EEG signal", "title": f"{name} {_level(top['z_score'])}",
                          "detail": f"{top['label']} = {top['value']:.3f} (z={top['z_score']:+.1f} vs. model reference). "
                                    f"Background: {why}."})
        steps.append({"stage": "Estimated state", "title": emotion["label"],
                      "detail": f"AI-estimated valence {emotion['valence']:.0%}, arousal {emotion['arousal']:.0%}, focus "
                                f"{emotion['focus']:.0%}, stress tendency {emotion['stress']:.0%} (model confidence "
                                f"{emotion['confidence']:.0%}{', signal quality ' + quality_label if quality_label else ''})."})
    if text_analysis and text_analysis.get("emotions"):
        steps.append({"stage": "Language", "title": ", ".join(text_analysis["emotions"][:3]),
                      "detail": f"Your description was parsed ({text_analysis.get('provider', 'rules')}); intent: "
                                f"{text_analysis.get('intent', 'unspecified')}."})
    strat = ("Match the current state" if plan["mode"] == "match" else
             f"Shift toward '{plan['target_key']}' by {plan['shift']:.0%} using a gradual arc")
    steps.append({"stage": "Music strategy", "title": strat,
                  "detail": f"{profile['genre']} · {profile['bpm']} BPM · {profile['mode_name']} · {profile['texture']} · "
                            f"{', '.join(profile['instrumentation'][:4])}."})
    reason = (
        f"The selected tempo ({profile['bpm']} BPM) and {profile['percussion'] if profile['percussion'] != 'none' else 'no percussion'} "
        f"follow the {'current' if plan['mode'] == 'match' else 'blended current/target'} arousal level "
        f"({plan['music']['arousal']:.0%}); the {profile['scale']} mode follows valence ({plan['music']['valence']:.0%})."
    )
    if plan["mode"] == "shift":
        reason += (" Music therapy's 'iso principle' suggests starting near the listener's state and moving gradually, "
                   "so early stages stay close to the current state and later stages approach the target.")
    steps.append({"stage": "Reason", "title": preset["title"] if preset else "Profile-driven", "detail": reason})
    return {
        "steps": steps,
        "feature_importance": features[:8],
        "fusion_weights": weights or {},
        "caveats": [
            "Feature attributions are local perturbation estimates for this model, not causal brain mechanisms.",
            "The default model is a synthetic-data baseline; treat outputs as a demonstration of the pipeline.",
            DISCLAIMER,
        ],
    }
