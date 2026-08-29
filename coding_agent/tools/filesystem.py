from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from .registry import ToolContext, ToolError, ToolRegistry


def _safe_path(context: ToolContext, relative: str, *, allow_root: bool = False) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ToolError("path must be a non-empty relative string")
    root = context.root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError("path escapes the workspace root")
    if candidate == root and not allow_root:
        raise ToolError("workspace root is not a file")
    return candidate


def _read_file(context: ToolContext, args: dict[str, Any]) -> str:
    path = _safe_path(context, args.get("path", ""))
    if not path.is_file():
        raise ToolError(f"file not found: {args.get('path')}")
    max_chars = min(int(args.get("max_chars", 30000)), 100000)
    show_line_numbers = bool(args.get("show_line_numbers", True))
    start_line = max(1, int(args.get("start_line", 1)))
    max_lines = max(1, min(int(args.get("max_lines", 400)), 2000))
    lines = path.read_text(encoding="utf-8").splitlines()
    selected = lines[start_line - 1 : start_line - 1 + max_lines]
    if show_line_numbers:
        body = "\n".join(f"{index}|{line}" for index, line in enumerate(selected, start_line))
    else:
        body = "\n".join(selected)
    if start_line > 1 or len(lines) > len(selected):
        header = f"[FILE] {path.relative_to(context.root.resolve()).as_posix()} lines={len(lines)} showing={start_line}-{start_line + len(selected) - 1}\n"
        body = header + body
    return body[:max_chars]


def _write_file(context: ToolContext, args: dict[str, Any]) -> str:
    path = _safe_path(context, args.get("path", ""))
    content = args.get("content")
    if not isinstance(content, str):
        raise ToolError("content must be a string")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content)} characters to {path.relative_to(context.root.resolve())}"


def _edit_file(context: ToolContext, args: dict[str, Any]) -> str:
    path = _safe_path(context, args.get("path", ""))
    old = args.get("old")
    new = args.get("new")
    if not isinstance(old, str) or not isinstance(new, str):
        raise ToolError("old and new must be strings")
    content = path.read_text(encoding="utf-8")
    occurrences = content.count(old)
    if occurrences == 0:
        raise ToolError("old text was not found; read the file again and retry with an exact, smaller unique block")
    expected = int(args.get("expected_occurrences", 1))
    if occurrences != expected:
        raise ToolError(f"expected {expected} occurrence(s), found {occurrences}")
    path.write_text(content.replace(old, new), encoding="utf-8")
    return f"OK: replaced {occurrences} occurrence(s) in {path.relative_to(context.root.resolve())}"


def _list_dir(context: ToolContext, args: dict[str, Any]) -> str:
    directory = _safe_path(context, args.get("path", "."), allow_root=True)
    if not directory.is_dir():
        raise ToolError(f"directory not found: {args.get('path')}")
    recursive = bool(args.get("recursive", False))
    paths = directory.rglob("*") if recursive else directory.iterdir()
    visible = [p for p in paths if ".git" not in p.parts and ".agent" not in p.parts]
    visible.sort(key=lambda p: (p.is_file(), str(p).lower()))
    lines = []
    for path in visible[:500]:
        marker = "[file]" if path.is_file() else "[dir]"
        lines.append(f"{marker} {path.relative_to(context.root.resolve()).as_posix()}")
    return "\n".join(lines) or "(empty directory)"


def _search(context: ToolContext, args: dict[str, Any]) -> str:
    query = args.get("query")
    if not isinstance(query, str) or not query:
        raise ToolError("query must be a non-empty string")
    pattern = args.get("glob", "*")
    regex = re.compile(query, re.IGNORECASE) if args.get("regex", False) else None
    results: list[str] = []
    for path in context.root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".agent" in path.parts:
            continue
        if not fnmatch.fnmatch(path.name, pattern):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            matched = bool(regex.search(line)) if regex else query.lower() in line.lower()
            if matched:
                results.append(f"{path.relative_to(context.root).as_posix()}:{number}: {line[:300]}")
                if len(results) >= 200:
                    return "\n".join(results) + "\n(results truncated)"
    return "\n".join(results) or "(no matches)"


def register_filesystem_tools(registry: ToolRegistry) -> None:
    registry.register(
        "list_dir",
        "List files and directories inside the workspace.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative directory path. Use '.' for the root."},
                "recursive": {"type": "boolean", "description": "Whether to include nested files."},
            },
            "required": ["path"],
        },
        _list_dir,
    )
    registry.register(
        "read_file",
        "Read a UTF-8 text file from the workspace.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path."},
                "max_chars": {"type": "integer", "description": "Maximum characters to return."},
                "start_line": {"type": "integer", "description": "First 1-based line to read, default 1."},
                "max_lines": {"type": "integer", "description": "Maximum lines to read, default 400."},
                "show_line_numbers": {"type": "boolean", "description": "Prefix lines with line numbers, default true."},
            },
            "required": ["path"],
        },
        _read_file,
    )
    registry.register(
        "write_file",
        "Create or overwrite a UTF-8 text file inside the workspace.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path."},
                "content": {"type": "string", "description": "Full file content."},
            },
            "required": ["path", "content"],
        },
        _write_file,
    )
    registry.register(
        "edit_file",
        "Replace exact text in a UTF-8 text file. The replacement only succeeds when the occurrence count matches.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path."},
                "old": {"type": "string", "description": "Exact text to replace."},
                "new": {"type": "string", "description": "Replacement text."},
                "expected_occurrences": {"type": "integer", "description": "Expected number of matches, default 1."},
            },
            "required": ["path", "old", "new"],
        },
        _edit_file,
    )
    registry.register(
        "search",
        "Search UTF-8 text files under the workspace.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text or regex to search for."},
                "glob": {"type": "string", "description": "Filename glob, for example '*.py'."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
            },
            "required": ["query"],
        },
        _search,
    )


class FileSystemTools:
    """Compatibility wrapper used by callers that prefer an object-oriented setup."""

    register = staticmethod(register_filesystem_tools)
