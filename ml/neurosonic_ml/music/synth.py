"""Local generative music renderer (numpy). Turns a music profile into real audio.

Layers: harmonic pads, bass, plucked/piano/bell arpeggio, optional percussion, airy noise bed,
convolution reverb. For SHIFT mode a list of stage profiles is rendered back-to-back with
crossfades so tempo, brightness and instrumentation evolve across the track (iso principle).
"""
from __future__ import annotations

import io
import math
import wave

import numpy as np
from scipy import signal

from .profile import MODES, ROOT_SEMITONE

SR = 22050
MAX_SECONDS = 90


def _midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n: int, attack: int, release: int) -> np.ndarray:
    e = np.ones(n)
    a, r = min(attack, n // 2), min(release, n // 2)
    if a > 0:
        e[:a] = np.linspace(0, 1, a) ** 1.5
    if r > 0:
        e[-r:] *= np.linspace(1, 0, r) ** 1.5
    return e


def _tone(freq: float, n: int, harmonics: int, detune_cents: float = 0.0, bright: float = 0.5) -> np.ndarray:
    # one complex exponential, harmonics by repeated multiplication (much cheaper than N sin() calls)
    f = freq * 2 ** (detune_cents / 1200)
    base = np.exp(2j * np.pi * f / SR * np.arange(n))
    cur = base.copy()
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        out += (1.0 / (k ** (1.6 - 0.8 * bright))) * cur.imag
        if k < harmonics:
            cur *= base
    return out


def _chords(profile: dict, n_bars: int, rng: np.random.RandomState) -> list[list[int]]:
    scale = MODES[profile["scale"]]
    root = 48 + ROOT_SEMITONE[profile["key"]]
    minorish = profile["scale"] in ("aeolian", "dorian", "phrygian")
    progs = [[0, 5, 2, 6], [0, 3, 6, 4], [0, 5, 3, 4]] if minorish else [[0, 4, 5, 3], [0, 3, 4, 3], [0, 5, 3, 4]]
    prog = progs[rng.randint(len(progs))]
    cx = profile["harmonic_complexity"]
    steps = [0, 2, 4] + ([6] if cx > 0.42 else []) + ([8] if cx > 0.7 else [])
    chords = []
    for b in range(n_bars):
        d = prog[b % len(prog)]
        chords.append([root + scale[(d + s) % 7] + 12 * ((d + s) // 7) for s in steps])
    return chords


def _render_segment(profile: dict, dur: float, rng: np.random.RandomState, timbre: str) -> np.ndarray:
    n_total = int(dur * SR)
    beat = 60.0 / profile["bpm"]
    bar = 4 * beat
    n_bars = max(1, int(math.ceil(dur / bar)))
    out = np.zeros(n_total + int(bar * SR) + SR)
    chords = _chords(profile, n_bars, rng)
    bright, dens, energy = profile["brightness"], profile["rhythm_density"], profile["energy"]
    harm = 2 + int(bright * 3.5)
    bar_n = int(bar * SR)

    for b, chord in enumerate(chords):
        s0 = b * bar_n
        # pads: two detuned voices per chord tone
        for m in chord:
            f = _midi_hz(m)
            for dc in (-4.0, 4.0):
                x = _tone(f, bar_n + int(0.6 * SR), harm, dc, bright)
                out[s0:s0 + len(x)] += 0.05 * x * _env(len(x), int(0.7 * SR), int(0.9 * SR))
        # bass
        bass_f = _midi_hz(chord[0] - 24)
        hits = 1 if energy < 0.4 else 2
        seg = bar_n // hits
        for h in range(hits):
            x = _tone(bass_f, seg, 2, 0, 0.1)
            out[s0 + h * seg:s0 + h * seg + seg] += 0.18 * x * _env(seg, int(0.05 * SR), int(0.25 * SR))
        # arpeggio / melodic layer
        if dens > 0.18:
            step_beats = 0.5 if dens < 0.6 else 0.25
            n_steps = int(4 / step_beats)
            p_play = 0.35 + 0.6 * dens
            order = rng.permutation(len(chord)) if rng.rand() < 0.5 else np.arange(len(chord))
            for i in range(n_steps):
                if rng.rand() > p_play:
                    continue
                m = chord[order[i % len(chord)]] + 12 * (1 + int(rng.rand() < 0.3))
                f = _midi_hz(m)
                ln = int(min(0.9, 0.35 + 0.5 * (1 - dens)) * SR)
                t = np.arange(ln) / SR
                if timbre == "piano":
                    x = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-3 * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-6 * t)
                    x *= np.exp(-3.2 * t)
                elif timbre == "bell":
                    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-4 * t) + 0.3 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-8 * t)
                    x *= np.exp(-2.2 * t)
                elif timbre == "synth":
                    x = signal.sawtooth(2 * np.pi * f * t) * 0.4 + 0.6 * np.sin(2 * np.pi * f * t)
                    x *= np.exp(-5 * t) * (0.5 + bright)
                else:  # pluck / pad-ish
                    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)
                    x *= np.exp(-4.5 * t)
                x *= 0.09 * (0.7 + 0.5 * rng.rand())
                st = s0 + int(i * step_beats * beat * SR)
                out[st:st + ln] += x
        # percussion
        if profile["percussion"] != "none":
            for q in range(4):
                st = s0 + int(q * beat * SR)
                if (energy > 0.5 and dens > 0.45) or q in (0, 2):
                    kn = int(0.2 * SR)
                    t = np.arange(kn) / SR
                    k = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 28)) / SR)
                    gain = 0.30 if dens > 0.45 else 0.14
                    out[st:st + kn] += gain * k * np.exp(-t * 14)
                if dens > 0.45:
                    for off in (0.5,):
                        hn = int(0.05 * SR)
                        h = rng.randn(hn)
                        h = signal.lfilter(*signal.butter(2, 6000 / (SR / 2), "highpass"), h)
                        pos = st + int(off * beat * SR)
                        out[pos:pos + hn] += 0.05 * h * np.exp(-np.arange(hn) / SR * 90)

    out = out[:n_total]
    # airy noise bed
    cx = 0.015 * (0.4 + profile["reverb"])
    noise = signal.lfilter(*signal.butter(2, (900 + 3500 * bright) / (SR / 2), "lowpass"), rng.randn(n_total))
    out += cx * noise
    return out


def _reverb(x: np.ndarray, amount: float, rng: np.random.RandomState) -> np.ndarray:
    ir_len = int(SR * (0.8 + 1.8 * amount))
    t = np.arange(ir_len) / SR
    ir = rng.randn(ir_len) * np.exp(-t * (5.5 - 3.5 * amount))
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    wet = signal.fftconvolve(x, ir)[: len(x)]
    mix = 0.15 + 0.35 * amount
    return (1 - mix) * x + mix * wet * 1.3


def render(stages: list[dict], duration: float = 30.0, seed: int = 1, timbre: str | None = None, sr_out: int = SR) -> np.ndarray:
    """Render stage profile(s) into a mono float array in [-1, 1]."""
    duration = float(min(max(duration, 4.0), MAX_SECONDS))
    rng = np.random.RandomState(seed)
    n_st = len(stages)
    seg_dur = duration / n_st
    xfade = int(min(1.5, seg_dur / 3) * SR)
    pieces = []
    for st in stages:
        seg = _render_segment(st, seg_dur + (xfade / SR), rng, timbre or st.get("timbre", "pad"))
        pieces.append(seg)
    out = pieces[0]
    for seg in pieces[1:]:
        if xfade > 0:
            fade = np.linspace(0, 1, xfade)
            out[-xfade:] = out[-xfade:] * (1 - fade) + seg[:xfade] * fade
            out = np.concatenate([out, seg[xfade:]])
        else:
            out = np.concatenate([out, seg])
    out = out[: int(duration * SR)]
    out = _reverb(out, float(np.mean([s["reverb"] for s in stages])), rng)
    dyn = {"pp": 0.55, "p": 0.65, "mp": 0.75, "mf": 0.85, "f": 0.92}[stages[-1]["dynamics"]]
    out *= _env(len(out), int(1.5 * SR), int(2.0 * SR))
    out = np.tanh(out * 1.4)  # soft limiter
    out = out / (np.max(np.abs(out)) + 1e-9) * dyn
    return out.astype(np.float32)


def to_wav_bytes(x: np.ndarray, sr: int = SR) -> bytes:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
