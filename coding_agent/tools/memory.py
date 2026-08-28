from __future__ import annotations

from typing import Any

from ..memory import ProjectMemoryStore, format_entries
from .registry import ToolContext, ToolError, ToolRegistry


def _memory_record(context: ToolContext, args: dict[str, Any]) -> str:
    section = args.get("section", "note")
    content = args.get("content")
    title = args.get("title", "")
    tags = args.get("tags", [])
    if not isinstance(section, str):
        raise ToolError("section must be a string")
    if not isinstance(content, str):
        raise ToolError("content must be a string")
    if not isinstance(title, str):
        raise ToolError("title must be a string")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ToolError("tags must be a list of strings")
    try:
        entry = ProjectMemoryStore(context.root).record(section, content, title=title, tags=tags)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return f"OK: recorded memory {entry.id} [{entry.section}]"


def _memory_read(context: ToolContext, args: dict[str, Any]) -> str:
    query = args.get("query", "")
    section = args.get("section")
    limit = args.get("limit", 8)
    if not isinstance(query, str):
        raise ToolError("query must be a string")
    if section is not None and not isinstance(section, str):
        raise ToolError("section must be a string")
    entries = ProjectMemoryStore(context.root).search(query, section=section, limit=int(limit))
    return format_entries(entries)


def register_memory_tools(registry: ToolRegistry) -> None:
    registry.register(
        "memory_record",
        "Persist a concise project memory entry for future agent runs.",
        {
            "type": "object",
            "properties": {
                "section": {"type": "string", "enum": ["work", "lessons", "actions", "note"]},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["section", "content"],
        },
        _memory_record,
    )
    registry.register(
        "memory_read",
        "Read local project memory by recency or lexical query.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "section": {"type": "string", "enum": ["work", "lessons", "actions", "note"]},
                "limit": {"type": "integer"},
            },
        },
        _memory_read,
    )


class MemoryTools:
    register = staticmethod(register_memory_tools)
