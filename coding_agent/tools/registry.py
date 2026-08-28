from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolContext:
    root: Path
    command_timeout: float = 20.0
    max_output_chars: int = 12000
    approve_commands: Callable[[str], bool] | None = None
    enforce_command_safety: bool = True


Handler = Callable[[ToolContext, dict[str, Any]], str]


class ToolRegistry:
    def __init__(self, context: ToolContext):
        self.context = context
        self._handlers: dict[str, tuple[dict[str, Any], Handler]] = {}

    def register(self, name: str, description: str, parameters: dict[str, Any], handler: Handler) -> None:
        if name in self._handlers:
            raise ValueError(f"tool already registered: {name}")
        self._handlers[name] = (
            {"name": name, "description": description, "parameters": parameters},
            handler,
        )

    def definitions(self) -> list[dict[str, Any]]:
        return [spec for spec, _ in self._handlers.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        item = self._handlers.get(name)
        if item is None:
            return f"ERROR: unknown tool '{name}'. Available: {', '.join(self._handlers)}"
        _, handler = item
        try:
            return handler(self.context, arguments)
        except (ToolError, OSError, ValueError, TypeError) as exc:
            return f"ERROR: {exc}"

    def schema_text(self) -> str:
        return json.dumps(self.definitions(), ensure_ascii=False, indent=2)
