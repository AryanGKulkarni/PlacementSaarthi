"""Chat completion via Ollama (/api/chat)."""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class LLMError(Exception):
    """Ollama couldn't generate an answer (down, model missing, timeout, bad response)."""


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    duration_ms: int | None


class LLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.model

    def chat(self, messages: list[Message]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "keep_alive": settings.llm_keep_alive,
            "options": {
                "temperature": settings.llm_temperature,
                "num_ctx": settings.llm_num_ctx,
                "num_predict": settings.llm_max_tokens,
            },
        }
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=settings.llm_timeout)
        except httpx.TimeoutException as exc:
            raise LLMError(f"LLM timed out after {settings.llm_timeout:.0f}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama not reachable at {self.base_url}: {exc}") from exc

        if response.status_code == 404:
            raise LLMError(
                f"LLM model '{self.model}' not found in Ollama. "
                f"Run: docker compose exec ollama ollama pull {self.model}"
            )
        if response.status_code != 200:
            raise LLMError(f"Ollama error {response.status_code}: {response.text[:300]}")

        data = response.json()
        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise LLMError("LLM returned an empty answer")

        total_ns = data.get("total_duration")
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            duration_ms=int(total_ns / 1_000_000) if total_ns else None,
        )
