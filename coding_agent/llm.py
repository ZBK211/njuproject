from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings


@dataclass(frozen=True)
class ModelResponse:
    text: str
    raw: dict[str, Any]


class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> ModelResponse: ...


class LLMError(RuntimeError):
    pass


class OpenAICompatibleModel:
    """Minimal Chat Completions client using urllib, with no agent SDK dependency."""

    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise LLMError("OPENAI_API_KEY is not configured")
        self.settings = settings

    def complete(self, messages: list[dict[str, str]]) -> ModelResponse:
        payload = json.dumps(
            {"model": self.settings.model, "messages": messages, "temperature": 0}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"model request failed with HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(f"model request failed: {exc}") from exc
        try:
            text = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("model response has no choices[0].message.content") from exc
        if not isinstance(text, str):
            raise LLMError("model response content is not text")
        return ModelResponse(text=text, raw=raw)
