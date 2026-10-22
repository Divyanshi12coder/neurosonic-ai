# AI Models

## Emotion model (`ml/neurosonic_ml/emotion/`)
- **Task:** regress five 0-1 dimensions (valence, arousal, calmness, focus, stress tendency) from 13 EEG features.
- **Model:** multi-output `RandomForestRegressor` (160 trees, `min_samples_leaf=2`). A sensible baseline for small tabular data:
  handles non-linear ratios, needs no scaling, and its per-tree spread gives a confidence heuristic and importances.
- **Shipped artefact:** `models/emotion_rf.joblib`, trained on **synthetic** EEG from the simulator (`scripts/train_emotion.py`).
  Every API response and the UI label it as a demonstration baseline (`is_demo_baseline: true`).
- **Held-out metrics:** stored in `models/emotion_rf.meta.json` and exposed by `/api/health`. They are measured on a held-out split of
  *synthetic* data, so they only show the model can invert the simulator (focus and valence are weakest because the simulator ties
  them to few spectral cues). **They are not evidence of real-world accuracy and are not presented as such.**
- **Confidence:** `agreement x (0.4 + 0.6 x signal_quality)` with agreement = 1 - 3.5 x mean tree std. A heuristic, not a calibrated probability.
- **Explainability:** local perturbation attribution (replace a feature by its training mean, measure the change in all five outputs)
  plus global impurity importance, shown in "Why this music?".

### Training on real data (DEAP)
```bash
python scripts/train_emotion.py --dataset deap --path <data_preprocessed_python> --loso
```
DEAP is licensed and not bundled (request access at https://www.eecs.qmul.ac.uk/mmv/datasets/deap/). Only valence and arousal are real
labels; calmness and stress are derived proxies and focus is constant (documented in `dataset.load_deap`). `--loso` reports
subject-independent grouped cross-validation, the only honest estimate. Channels are mapped by name, so frontal asymmetry uses AF3/AF4.
The new artefact in `models/` is loaded automatically. The loader is unit-tested against a fabricated file only; it has not been run on real DEAP data.

## Mood to music (`music/`)
1. **Fusion** - confidence-weighted average of EEG estimate, language-derived state and a small prior from recent history; weights are returned to the UI.
2. **Plan** - MATCH mirrors the state. SHIFT builds a 4-stage trajectory from the current state toward a target (calm / focus / energize / refresh), scaled by the slider (iso principle).
3. **Profile** - arousal drives BPM (48-150), rhythm density and dynamics; valence drives mode (lydian ... phrygian) and brightness; calmness drives reverb; stated preferences pick timbre.
4. **Recommendation** - 24 generative presets ranked by weighted distance in mood space + preference tags + favourites + learned ratings.
5. **Generation** - `LocalSynthProvider` renders pads, bass, arpeggio, percussion and reverb in numpy; SHIFT renders its stages back-to-back with cross-fades.

NeuroSonic ships no copyrighted songs: the "catalog" is a set of generative presets rendered on demand.

## NLP + LLM (`ml/nlp/`)
A rule-based parser (affect lexicon with negation, intent patterns, preference and context words) always runs. If `LLM_API_KEY` is set, an
OpenAI-compatible model returns JSON that is **validated, clipped and merged** with the rules output; any failure falls back silently to rules.

## Evaluation framework
- Signal pipeline: unit tests with injected sinusoids (`tests/test_eeg_pipeline.py`).
- Emotion model: held-out split plus `--loso` on DEAP (user-supplied data).
- Recommendation: unit tests on ordering and personalisation. Before/after mood feedback is collected (`POST /api/music/feedback`) but no outcome results are claimed.
