"""Groq OpenAI-compatible chat adapter."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from zomato_ai.config import AppSettings, require_llm_settings

LOGGER = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when the LLM call fails."""


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return raw assistant content for a chat completion."""


class GroqLLMClient:
    """Minimal Groq client using the OpenAI-compatible chat completions API."""

    def __init__(self, settings: AppSettings) -> None:
        require_llm_settings(settings)
        self.settings = settings

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise LLMError("Groq returned empty assistant content")
                return content
            except (httpx.HTTPError, KeyError, IndexError, TypeError, LLMError) as exc:
                last_error = exc
                LOGGER.warning("Groq completion attempt failed attempt=%s", attempt + 1)

        raise LLMError("Groq completion failed") from last_error

