"""Parsing + validation of uploaded EEG recordings (CSV / JSON)."""
from __future__ import annotations

import io
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

MAX_CHANNELS = 32
MAX_SECONDS = 900
MIN_SECONDS = 2.0
TIME_COLS = {"time", "timestamp", "t", "ts", "time_s"}


class EEGFormatError(ValueError):
    pass


@dataclass
class Recording:
    fs: float
    channels: list[str]
    data: np.ndarray  # (channels, samples) in µV

    @property
    def duration(self) -> float:
        return self.data.shape[1] / self.fs


def _validate(fs: float, names: list[str], data: np.ndarray) -> Recording:
    if not np.isfinite(fs) or not (32 <= fs <= 2048):
        raise EEGFormatError("sampling rate must be between 32 and 2048 Hz")
    if data.ndim != 2 or data.shape[0] < 1:
        raise EEGFormatError("no EEG channels found")
    if data.shape[0] > MAX_CHANNELS:
        raise EEGFormatError(f"too many channels (max {MAX_CHANNELS})")
    if not np.isfinite(data).all():
        raise EEGFormatError("data contains NaN/Inf values")
    dur = data.shape[1] / fs
    if dur < MIN_SECONDS:
        raise EEGFormatError(f"recording too short ({dur:.1f}s); need at least {MIN_SECONDS:.0f}s")
    if dur > MAX_SECONDS:
        raise EEGFormatError(f"recording too long ({dur:.0f}s); max {MAX_SECONDS}s")
    return Recording(fs=float(fs), channels=names, data=data.astype(float))


def parse_csv(content: bytes | str, fs: float | None = None) -> Recording:
    try:
        text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:  # noqa: BLE001
        raise EEGFormatError(f"could not parse CSV: {e}") from e
    time_col = next((c for c in df.columns if str(c).strip().lower() in TIME_COLS), None)
    if time_col is not None:
        t = pd.to_numeric(df[time_col], errors="coerce").to_numpy()
        dt = np.median(np.diff(t[np.isfinite(t)])) if np.isfinite(t).sum() > 2 else np.nan
        if fs is None and np.isfinite(dt) and dt > 0:
            # timestamps in ms if the step is > 1
            fs = 1000.0 / dt if dt > 1.0 else 1.0 / dt
        df = df.drop(columns=[time_col])
    num = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    if num.shape[1] == 0:
        raise EEGFormatError("CSV has no numeric channel columns")
    if num.isna().any().any():
        num = num.interpolate(limit_direction="both")
    if fs is None:
        raise EEGFormatError("sampling rate unknown: provide a time column or the `fs` field")
    return _validate(fs, [str(c).strip() for c in num.columns], num.to_numpy().T)


def parse_json(content: bytes | str, fs: float | None = None) -> Recording:
    try:
        obj = json.loads(content)
    except Exception as e:  # noqa: BLE001
        raise EEGFormatError(f"invalid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise EEGFormatError("JSON root must be an object")
    fs = float(obj.get("fs") or obj.get("sampling_rate") or fs or 0) or None
    if fs is None:
        raise EEGFormatError("JSON must include `fs` (sampling rate in Hz)")
    try:
        if isinstance(obj.get("data"), dict):
            names = list(obj["data"].keys())
            arr = np.array([obj["data"][k] for k in names], dtype=float)
        elif "samples" in obj:  # rows = samples, cols = channels
            arr = np.array(obj["samples"], dtype=float).T
            names = obj.get("channels") or [f"ch{i + 1}" for i in range(arr.shape[0])]
        elif "channels" in obj and isinstance(obj["channels"], dict):
            names = list(obj["channels"].keys())
            arr = np.array([obj["channels"][k] for k in names], dtype=float)
        else:
            raise EEGFormatError("JSON needs `data` {channel: [..]} or `samples` [[..]]")
    except EEGFormatError:
        raise
    except Exception as e:  # noqa: BLE001
        raise EEGFormatError(f"malformed EEG arrays: {e}") from e
    return _validate(fs, [str(n) for n in names], arr)


def parse_upload(filename: str, content: bytes, fs: float | None = None) -> Recording:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return parse_csv(content, fs)
    if name.endswith(".json"):
        return parse_json(content, fs)
    raise EEGFormatError("unsupported file type (use .csv or .json)")
