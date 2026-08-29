from __future__ import annotations

import shutil
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_agent.agent import Agent
from examples.demo_model import DemoModel
from examples.demo_model import TextToolsDemoModel


TASKS = {
    "fizzbuzz": {
        "path": "demo_workspace_template",
        "task": "Implement the FizzBuzz task in the workspace and verify it with tests.",
        "model": DemoModel,
    },
    "text_tools": {
        "path": "text_tools_workspace_template",
        "task": "Implement normalize_words(text) in text_tools.py and verify it with tests.",
        "model": TextToolsDemoModel,
    },
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run a deterministic offline ForgeAgent demo.")
    parser.add_argument("--template", choices=sorted(TASKS), default="fizzbuzz")
    parser.add_argument("--task", help="Override the default task prompt.")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    spec = TASKS[args.template]
    source = project_root / "examples" / spec["path"]
    workspace = project_root / "demo_workspace" / f"offline_cli_{args.template}"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    agent = Agent(spec["model"](), workspace, max_steps=8, approve_commands=lambda command: True)
    result = agent.run(args.task or spec["task"], on_event=_print_event)
    print(f"\nRESULT: {result.status}; steps={result.steps}\n{result.answer}")
    memory_file = workspace / ".agent" / "PROJECT_MEMORY.md"
    if memory_file.exists():
        print("\nPROJECT MEMORY")
        print(memory_file.read_text(encoding="utf-8"))
    return 0 if result.status == "completed" else 1


def _print_event(kind: str, step: int, text: str) -> None:
    if kind == "model" and len(text) > 500:
        text = text[:500] + "...(truncated for demo output)"
    print(f"[{kind.upper()} {step}] {text}")


if __name__ == "__main__":
    raise SystemExit(main())
