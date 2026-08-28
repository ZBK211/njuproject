from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import Agent
from .config import Settings
from .llm import OpenAICompatibleModel


def _print_event(kind: str, step: int, text: str) -> None:
    prefix = {"model": "MODEL", "tool": "TOOL", "observation": "INFO"}.get(kind, kind.upper())
    print(f"\n[{prefix} step={step}]\n{text}")


def main() -> int:
    parser = argparse.ArgumentParser(description="A hand-built coding agent")
    parser.add_argument("task", nargs="?", help="programming task for the agent")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace root")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--yes", action="store_true", help="approve non-blocked shell commands without prompting")
    args = parser.parse_args()
    task = args.task or input("Task> ").strip()
    settings = Settings.from_env()
    model = OpenAICompatibleModel(settings)
    agent = Agent(model, args.root, max_steps=args.max_steps, approve_commands=_make_approval(args.yes))
    result = agent.run(task, on_event=_print_event)
    print(f"\n[{result.status}] steps={result.steps}\n{result.answer}")
    return 0 if result.status == "completed" else 1


def _make_approval(auto_yes: bool):
    if auto_yes:
        return lambda command: True

    def approve(command: str) -> bool:
        if not sys.stdin.isatty():
            return False
        answer = input(f"Approve shell command? {command}\n[y/N] ").strip().lower()
        return answer in {"y", "yes"}

    return approve


if __name__ == "__main__":
    raise SystemExit(main())
