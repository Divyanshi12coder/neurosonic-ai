# Research Notes

Concepts the design draws on. Claims are intentionally modest; see `ml/neurosonic_ml/rag/knowledge/` for the retrieval corpus.
References are pointers for further reading and should be checked against the originals.

| Topic | Use in NeuroSonic | Pointers |
|---|---|---|
| Circumplex model of affect | Valence/arousal as the core 2-D state and the Mood Compass | Russell (1980) |
| EEG frequency bands | Band-power features; alpha/beta/theta interpretations | Buzsaki, *Rhythms of the Brain*; Klimesch (1999) |
| Frontal alpha asymmetry | One valence-related feature; weak and debated | Davidson (1992); Coan & Allen (2004) |
| Engagement index beta/(alpha+theta) | Arousal/engagement feature | Pope, Bogart & Bartolome (1995) |
| EEG emotion datasets | Training pipeline structure | DEAP (Koelstra et al., 2012); SEED (Zheng & Lu, 2015) |
| Welch PSD | Stable spectral estimate | Welch (1967) |
| Music and perceived emotion | arousal -> tempo/density; valence -> mode/brightness | Juslin & Laukka (2003) |
| Music listening and regulation | MATCH vs SHIFT strategies | Saarikallio & Erkkila (2007) |
| Iso principle | Staged SHIFT trajectory | Music-therapy literature |

## Honest limits
Scalp EEG emotion recognition generalises poorly across people and devices; labels are subjective; consumer headbands have few channels;
muscle and eye artifacts contaminate beta/gamma and frontal channels; and reported accuracies are often inflated by window-level leakage.
NeuroSonic therefore (1) labels its model as a synthetic baseline, (2) reports confidence and signal quality, (3) separates science from
inference in NeuroGuide, and (4) makes no clinical claims.

## Ideas for future validation
- Within-user calibration (resting baseline) and per-user z-scoring.
- A listening study using the built-in before/after feedback with a no-music control.
- Subject-independent training on DEAP/SEED with leave-one-subject-out evaluation.
