from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_agent.agent import Agent
from examples.demo_model import DemoModel


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "examples" / "demo_workspace_template"
    workspace = project_root / "demo_workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(source, workspace)
    agent = Agent(DemoModel(), workspace, max_steps=8, approve_commands=lambda command: True)
    result = agent.run("Implement the FizzBuzz task in the workspace and verify it with tests.", on_event=_print_event)
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
