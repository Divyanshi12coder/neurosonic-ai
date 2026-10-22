# EEG-Based Emotion Recognition

Affective computing studies how to estimate emotional states from signals such as speech, face, physiology and EEG. EEG-based emotion recognition typically follows a common pipeline: acquire signals, remove artifacts and filter, extract features, and train a classifier or regressor against emotion labels.

## Emotion models
Most studies use either discrete categories (happy, sad, fear) or the circumplex model of affect, which places emotions on two dimensions: valence (unpleasant to pleasant) and arousal (calm to excited). NeuroSonic represents state primarily as valence and arousal, with derived calmness, focus and stress-tendency scores.

## Common features
- Band power and relative band power (delta, theta, alpha, beta, gamma)
- Frontal alpha asymmetry: the difference in log alpha power between right and left frontal electrodes. Some studies relate relatively greater left-frontal activity to approach motivation and positive affect, but results are inconsistent across studies and it is considered a weak marker.
- Ratios such as theta/beta and beta/(alpha+theta), used as rough indices of arousal or engagement.
- Spectral entropy, Hjorth parameters, differential entropy and connectivity measures.

## Datasets
Public datasets include DEAP (32 participants watching music videos, self-rated valence and arousal) and SEED (film clips, discrete emotion labels). Labels are self-reported and noisy.

## Reported performance and its limits
Published accuracies vary widely and are often optimistic. Many studies evaluate within-subject or leak windows from the same trial into training and test sets. Subject-independent evaluation (training and testing on different people) is substantially harder, and models rarely transfer across devices and recording sessions.
