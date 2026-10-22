# EEG Signal Processing Basics

Raw scalp EEG has microvolt amplitudes and is dominated by noise and artifacts, so processing is essential before any feature is trusted.

## Filtering
A band-pass filter (for example 0.5–45 Hz) removes slow drift and high-frequency noise. A notch filter at 50 or 60 Hz removes mains interference. Zero-phase filtering (forward-backward) avoids phase distortion for offline analysis. Detrending removes linear drift.

## Artifacts
- Eye blinks and movements produce large, slow deflections at frontal channels, with amplitudes far above neural activity.
- Muscle activity (jaw clenching, frowning) adds broadband high-frequency power, especially above 20 Hz.
- Electrode contact problems produce flat lines or large noisy fluctuations.
Methods include amplitude thresholds, independent component analysis (ICA), and regression. NeuroSonic uses a simple quality score based on flat-line, large-amplitude and kurtosis checks, and reports the score alongside every estimate.

## Power spectral density
The Fast Fourier Transform (FFT) converts a window of samples into frequency components. Welch's method averages periodograms of overlapping windowed segments, which reduces variance and gives a more stable power estimate than a single FFT. Band power is the integral of PSD within a band; relative band power divides by total power to reduce the effect of overall amplitude differences between people and sessions.

## Other features
Spectral entropy measures how evenly power is spread across frequencies (flatter, noise-like spectra have higher entropy). Hjorth parameters describe activity (variance), mobility (mean frequency) and complexity of the signal in the time domain.

## Window length
Short windows give a fast response but noisy estimates; windows of several seconds give more stable band power. NeuroSonic uses 4-second windows.
