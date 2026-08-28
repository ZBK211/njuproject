# ForgeAgent

ForgeAgent is an inspectable coding agent built from Python's standard library. It uses an OpenAI-compatible chat model to plan one action at a time, execute local tools inside a selected workspace, feed observations back into the conversation, and stop only after a final response, an unrecoverable model error, or a step limit.

The project intentionally does not use LangChain, LlamaIndex, OpenAI Agents SDK, Claude Agent SDK, AutoGen, CrewAI, hosted code execution, or hosted file tools. The important mechanisms are implemented in this repository: message history, context compaction, tool schemas, workspace path checks, subprocess execution, JSON action parsing, error recovery, and termination policy.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_demo.py
```

For a real model, copy `.env.example` to a local `.env` or set the variables in the shell, then run:

```powershell
$env:OPENAI_API_KEY = "..."
python -m coding_agent "Add tests and improve the error handling" --root .
```

The runtime reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_TIMEOUT`. Secrets are never read from a tracked file. The CLI asks before running shell commands; pass `--yes` only in a trusted disposable workspace. Destructive commands such as recursive forced deletion, `git reset --hard`, and disk shutdown/format commands are blocked before approval.

## Architecture

`Agent` owns the loop and transcript. `ToolRegistry` owns explicit schemas and dispatch. File tools are workspace-scoped and shell output is bounded and time-limited. The model is an adapter behind a tiny protocol, so tests use a deterministic fake model without network access. `examples/demo_workspace_template` is the reproducible recording target.

The project also includes a local memory layer inspired by the design of `dsh-memoir`: completed tool-using runs are distilled into `.agent/memory.json`, rendered to `.agent/PROJECT_MEMORY.md`, retrieved with lexical BM25 over Chinese text, English words, and code identifiers, and injected into future runs as bounded Hot Memory. The memory feature is implemented in Python in this repository and does not require the DSH plugin runtime.

## Demo Output

`python scripts/run_demo.py` resets a small FizzBuzz workspace, lets the agent inspect and edit the file, runs pytest, then prints the generated project memory. A successful run shows:

```text
[TOOL 4] run_command: exit_code=0
.. [100%]
2 passed

RESULT: completed; steps=5
Implemented fizzbuzz(n) and verified it with pytest.

PROJECT MEMORY
## Work Log
- Agent run completed - Completed run using tools: list_dir, read_file, write_file, run_command.
```

## Development

Run `python -m pytest -q` after changes. Keep commits small and explanatory so the public repository shows the development process required by the assignment.

`THIRD_PARTY_NOTICES.md` records the memory-layer reference project and licensing note.
