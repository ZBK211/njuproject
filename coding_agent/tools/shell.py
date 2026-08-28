from __future__ import annotations

import subprocess
from typing import Any

from .registry import ToolContext, ToolError, ToolRegistry
from .safety import CommandSafetyPolicy


def _run_command(context: ToolContext, args: dict[str, Any]) -> str:
    command = args.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ToolError("command must be a non-empty string")
    if context.enforce_command_safety:
        decision = CommandSafetyPolicy().check(command)
        if not decision.allowed:
            return f"DENIED: command blocked by safety policy ({decision.reason})"
    if context.approve_commands is not None and not context.approve_commands(command):
        return "DENIED: command was not approved"
    timeout = min(float(args.get("timeout", context.command_timeout)), context.command_timeout)
    try:
        completed = subprocess.run(
            command,
            cwd=context.root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return f"TIMEOUT after {timeout:g}s\n{output[:context.max_output_chars]}"
    output = (completed.stdout or "") + (completed.stderr or "")
    output = output[:context.max_output_chars]
    return f"exit_code={completed.returncode}\n{output}" if output else f"exit_code={completed.returncode}"


def register_shell_tools(registry: ToolRegistry) -> None:
    registry.register(
        "run_command",
        "Run a local shell command in the workspace. Destructive commands are blocked and output is truncated.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute from the workspace root."},
                "timeout": {"type": "number", "description": "Optional timeout in seconds, capped by the runtime."},
            },
            "required": ["command"],
        },
        _run_command,
    )


class ShellTools:
    register = staticmethod(register_shell_tools)
