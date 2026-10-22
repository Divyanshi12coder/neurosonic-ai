# Limitations of EEG Emotion Inference

EEG-derived emotional states are estimates with substantial uncertainty and must not be treated as medical diagnoses or clinical assessments.

## Signal limitations
- Low signal-to-noise ratio: neural activity is tiny compared with artifacts from eyes, muscles and electrodes.
- Poor spatial resolution: scalp EEG blurs activity from many cortical sources, and consumer headbands record only a few channels.
- Hardware differences: electrode type, placement, reference and amplifier characteristics change the signal, so models trained on one device often transfer poorly to another.

## Individual variability
Baseline power, alpha peak frequency and responses to the same stimulus differ widely between people and within the same person across days. A model that ignores personal baselines can misread individual differences as emotional differences.

## Label problems
Emotion labels are usually self-reports collected after viewing short clips. They are subjective, delayed, culturally influenced and imprecise, and induced emotions in a lab are weaker than real-life emotions.

## Model and evaluation issues
Small datasets, window-level train/test leakage and within-subject evaluation inflate reported accuracy. Models can also encode dataset bias, for example when participants are mostly young university students.

## Interpretation
Band power tendencies are group-level statistical regularities. A rise in beta might mean concentration, anxiety or muscle tension; high alpha might mean relaxation or simply closed eyes. For these reasons NeuroSonic reports confidence and signal quality, labels its default model as a synthetic-data baseline, and phrases outputs as "AI-estimated".

## Ethics
Neural data is sensitive. Collect it only with informed consent, store it securely and give users control over deletion.
