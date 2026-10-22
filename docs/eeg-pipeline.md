# EEG Pipeline

Code: `ml/neurosonic_ml/eeg/`. The default montage is a 4-channel headband (TP9, AF7, AF8, TP10) at 256 Hz, but any channel
names and sampling rates of 32-2048 Hz are accepted.

## 1. Ingestion (`io.py`)
CSV (`time,ch1,ch2,...`; sampling rate inferred from the time column in seconds or ms, or provided as `fs`) and JSON
(`{"fs":256,"data":{"AF7":[...]}}` or `{"fs":..,"samples":[[..],..],"channels":[..]}`). Validation: 1-32 channels, finite values,
2 s - 15 min, max 5 MB (configurable). Failures raise `EEGFormatError`, surfaced as HTTP 422/413/415.

## 2. Preprocessing (`preprocessing.py`)
Linear detrend, notch (50 Hz default, `NOTCH_HZ`), then a 4th-order Butterworth band-pass 0.5-45 Hz applied zero-phase
(`sosfiltfilt`). The upper edge is clamped to 0.9 x Nyquist at low sampling rates.

## 3. Signal quality
Per channel, a 0-1 score penalising flat lines (std < 0.05 uV), the fraction of samples above 100 uV and excess kurtosis.
This is a heuristic, not a replacement for ICA/ASR artifact removal (see Limitations). The score feeds model confidence.

## 4. Features (`features.py`)
Welch PSD (2 s segments, 50% overlap). Bands: delta 1-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-45 Hz.

| Group | Features |
|---|---|
| Spectral | absolute + relative band power (per channel and mean), dominant frequency (4-30 Hz), spectral entropy (1-45 Hz, normalised) |
| Ratios | theta/beta, alpha/beta, engagement index beta/(alpha+theta) |
| Asymmetry | frontal alpha asymmetry ln(alpha_R) - ln(alpha_L) from AF7/AF8 (or AF3/AF4, F3/F4, Fp1/Fp2) |
| Temporal | variance, mean, std, skewness, kurtosis, line length, zero-crossing rate, Hjorth mobility/complexity |

The 13-element model input (`FEATURE_NAMES`) is dominated by **relative** quantities, which reduces sensitivity to amplitude
differences between people and hardware.

## 5. Synthetic generator (`synthetic.py`)
A latent state (valence, arousal, focus, stress, calm) sets the amplitude of three sinusoids per band per channel, plus slow amplitude
modulation, 1/f noise, white noise and periodic frontal eye-blink artifacts. Valence skews AF7/AF8 alpha (frontal asymmetry);
temporal sites get weaker beta/gamma. Scenarios: calm, focused, stressed, excited, drowsy, melancholic, and `auto`
(cycles every 24 s with 8 s cross-fades). Phase depends on absolute time, so successive windows form a continuous stream.

> This is a simulation that encodes widely reported tendencies. It demonstrates and tests the pipeline; it is not evidence about real brains.

## MNE
The project does not depend on MNE-Python, to keep installation light. `Recording.data` is a plain `(channels, samples)` array,
so `mne.io.Raw.get_data() * 1e6` can be passed straight to `analyze_window`.
