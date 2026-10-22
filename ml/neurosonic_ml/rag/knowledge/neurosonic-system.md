# How NeuroSonic Works (System Behaviour)

This document describes NeuroSonic's own design. It is system documentation, not neuroscience evidence.

## Pipeline
EEG window (4 s) -> preprocessing (detrend, notch, 0.5–45 Hz band-pass) -> quality score -> features (Welch PSD band powers, ratios, frontal alpha asymmetry, spectral entropy, Hjorth parameters) -> emotion model -> mood point -> music profile -> recommendation and audio generation.

## Emotion model
The default model is a random-forest regressor trained on synthetic EEG produced by a simulator that follows broad band-power tendencies. It is a baseline that demonstrates the pipeline; it is not validated on real people. It outputs valence, arousal, calmness, focus and stress tendency between 0 and 1, plus a heuristic confidence based on agreement between trees and signal quality. A model trained on a real dataset such as DEAP can be dropped in with the training script.

## High arousal classification
The system estimates high arousal mainly when relative beta power and the engagement index β/(α+θ) are high while relative alpha is low. This follows the tendency that alpha decreases and beta increases with alertness or tension. Because beta also increases with muscle tension, this is an estimate, not proof of a mental state.

## Mood to music
Arousal controls tempo, rhythmic density and dynamics; valence controls mode and brightness; calmness controls reverb and softness. In MATCH mode the music mirrors the current state. In SHIFT mode a trajectory moves from the current state toward a target (calm, focus, energize, refresh) following the iso principle.

## Fusion
When the user describes their feelings in text, a language model or rule-based parser extracts emotions and intent. The text-derived state is fused with the EEG estimate by confidence-weighted averaging, and the weights are shown to the user.

## Explanations
Feature attributions are computed by replacing each feature with its training mean and measuring the change in model output. They describe the model's behaviour, not brain mechanisms.
