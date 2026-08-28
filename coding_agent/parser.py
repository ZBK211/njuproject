from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


class ActionParseError(ValueError):
    """Raised when model output is not a valid agent action."""


@dataclass(frozen=True)
class Action:
    kind: str
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None


_FENCED_JSON = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _decode_json(text: str) -> dict[str, Any]:
    candidates = _FENCED_JSON.findall(text)
    candidates.append(text.strip())
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            value, _ = decoder.raw_decode(candidate.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ActionParseError("model output does not contain a JSON object")


def parse_action(text: str) -> Action:
    data = _decode_json(text)
    kind = data.get("kind")
    if kind == "final":
        answer = data.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ActionParseError("final action requires a non-empty string answer")
        return Action(kind="final", answer=answer.strip())
    if kind == "tool":
        tool = data.get("tool")
        arguments = data.get("arguments", {})
        if not isinstance(tool, str) or not tool.strip():
            raise ActionParseError("tool action requires a tool name")
        if not isinstance(arguments, dict):
            raise ActionParseError("tool arguments must be a JSON object")
        return Action(kind="tool", tool=tool.strip(), arguments=arguments)
    raise ActionParseError("action kind must be 'tool' or 'final'")

