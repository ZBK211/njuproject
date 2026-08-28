from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDecision:
    allowed: bool
    reason: str = ""


class CommandSafetyPolicy:
    """Small, inspectable guardrail for local shell execution."""

    _blocked_patterns = [
        (re.compile(r"\brm\s+(-[^\s]*r[^\s]*f|-?[^\s]*f[^\s]*r)\b", re.I), "recursive force delete"),
        (re.compile(r"\brmdir\b.*\s/(s|q)\b", re.I), "recursive directory removal"),
        (re.compile(r"\bdel\b.*\s/(s|q)\b", re.I), "recursive or quiet delete"),
        (re.compile(r"\bRemove-Item\b.*\s-(Recurse|Force)\b", re.I), "recursive or forced PowerShell removal"),
        (re.compile(r"\bgit\s+reset\s+--hard\b", re.I), "destructive git reset"),
        (re.compile(r"\bgit\s+clean\b.*-[^\s]*f", re.I), "destructive git clean"),
        (re.compile(r"\bformat\b\s+[A-Za-z]:", re.I), "disk format command"),
        (re.compile(r"\bshutdown\b|\brestart-computer\b", re.I), "system shutdown command"),
    ]

    def check(self, command: str) -> CommandDecision:
        normalized = " ".join(command.strip().split())
        for pattern, reason in self._blocked_patterns:
            if pattern.search(normalized):
                return CommandDecision(False, reason)
        return CommandDecision(True)
