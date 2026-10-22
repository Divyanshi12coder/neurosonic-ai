"""LLMProvider abstraction: OpenAI-compatible chat API, with a deterministic local fallback."""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 500, temperature: float = 0.2) -> str: ...


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI, Azure-compatible gateways, Ollama (`/v1`), vLLM, LM Studio, etc."""

    def __init__(self, api_key: str | None, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini", timeout: float = 30.0):
        self.api_key, self.base_url, self.model, self.timeout = api_key, base_url.rstrip("/"), model, timeout
        self.name = f"openai-compatible:{model}"

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, max_tokens: int = 500, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise LLMError("LLM_API_KEY not configured")
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            raise LLMError(f"LLM request failed: {e.__class__.__name__}") from e


class LocalFallbackProvider(LLMProvider):
    """No generative model: callers use rule-based/extractive paths when `available()` is False."""
    name = "local-rules"

    def available(self) -> bool:
        return False

    def complete(self, system: str, user: str, max_tokens: int = 500, temperature: float = 0.2) -> str:
        raise LLMError("no LLM configured; using local rule-based fallback")


def get_llm(api_key: str | None, base_url: str, model: str) -> LLMProvider:
    return OpenAICompatibleProvider(api_key, base_url, model) if api_key else LocalFallbackProvider()
