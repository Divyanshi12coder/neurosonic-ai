"""MusicProvider abstraction. `local-synth` always works (no key). `huggingface-musicgen` is optional."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from . import synth
from .profile import profile_to_prompt


class ProviderError(RuntimeError):
    pass


@dataclass
class GeneratedAudio:
    wav: bytes
    duration: float
    provider: str
    prompt: str
    sample_rate: int
    content_type: str = "audio/wav"


class MusicProvider(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(self, stages: list[dict], duration: float, seed: int, timbre: str | None) -> GeneratedAudio: ...


class LocalSynthProvider(MusicProvider):
    name = "local-synth"

    def available(self) -> bool:
        return True

    def generate(self, stages, duration, seed, timbre=None) -> GeneratedAudio:
        x = synth.render(stages, duration=duration, seed=seed, timbre=timbre)
        return GeneratedAudio(synth.to_wav_bytes(x), len(x) / synth.SR, self.name, profile_to_prompt(stages[-1]), synth.SR)


class HuggingFaceMusicGenProvider(MusicProvider):
    """Calls a hosted text-to-music model (default facebook/musicgen-small) with a prompt derived from the profile."""
    name = "huggingface-musicgen"

    def __init__(self, token: str | None, model: str = "facebook/musicgen-small", timeout: float = 120.0):
        self.token, self.model, self.timeout = token, model, timeout

    def available(self) -> bool:
        return bool(self.token)

    def generate(self, stages, duration, seed, timbre=None) -> GeneratedAudio:
        if not self.token:
            raise ProviderError("HF_API_TOKEN not set")
        prompt = profile_to_prompt(stages[-1])
        try:
            r = httpx.post(f"https://api-inference.huggingface.co/models/{self.model}",
                           headers={"Authorization": f"Bearer {self.token}"},
                           json={"inputs": prompt}, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"MusicGen request failed: {e.__class__.__name__}") from e
        ctype = r.headers.get("content-type", "audio/flac")
        if not ctype.startswith("audio/"):
            raise ProviderError("MusicGen returned non-audio response")
        return GeneratedAudio(r.content, duration, self.name, prompt, 32000, ctype)


def get_provider(name: str, hf_token: str | None = None) -> MusicProvider:
    """Return the requested provider, falling back to the local synth if it is unavailable."""
    if name == "huggingface-musicgen":
        p = HuggingFaceMusicGenProvider(hf_token)
        if p.available():
            return p
    return LocalSynthProvider()
