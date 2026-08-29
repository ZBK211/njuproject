from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .llm import ChatModel, LLMError
from .memory import ProjectMemoryStore, summarize_transcript
from .parser import ActionParseError, parse_action
from .tools.filesystem import register_filesystem_tools
from .tools.memory import register_memory_tools
from .tools.registry import ToolContext, ToolRegistry
from .tools.shell import register_shell_tools


@dataclass
class AgentResult:
    status: str
    answer: str
    steps: int
    transcript: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    def __init__(self, model: ChatModel, root: Path, *, max_steps: int = 12, max_context_chars: int = 50000, approve_commands=None):
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        context = ToolContext(root=root, approve_commands=approve_commands)
        self.registry = ToolRegistry(context)
        register_filesystem_tools(self.registry)
        register_shell_tools(self.registry)
        register_memory_tools(self.registry)
        self.model = model
        self.root = root
        self.max_steps = max_steps
        self.max_context_chars = max_context_chars
        self.memory = ProjectMemoryStore(root)

    def _system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "system.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        memory = self.memory.hot_memory()
        memory_block = f"\n\n{memory}" if memory else ""
        return prompt + memory_block + "\n\nTool definitions:\n" + self.registry.schema_text()

    def _compact(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        size = sum(len(message.get("content", "")) for message in messages)
        if size <= self.max_context_chars:
            return messages
        head = messages[:2]
        tail = messages[-8:]
        summary = {"kind": "context_note", "answer": "Earlier transcript was compacted to stay within the context budget."}
        return head + [{"role": "user", "content": json.dumps(summary)}] + tail

    def run(self, task: str, *, on_event=None) -> AgentResult:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": task},
        ]
        transcript: list[dict[str, Any]] = []
        parse_failures = 0
        for step in range(1, self.max_steps + 1):
            try:
                response = self.model.complete(self._compact(messages))
            except LLMError as exc:
                return AgentResult("error", f"模型调用失败：{exc}", step - 1, transcript)
            transcript.append({"step": step, "type": "model", "text": response.text})
            if on_event:
                on_event("model", step, response.text)
            messages.append({"role": "assistant", "content": response.text})
            try:
                action = parse_action(response.text)
                parse_failures = 0
            except ActionParseError as exc:
                parse_failures += 1
                observation = f"ERROR: invalid action JSON: {exc}. Return exactly one JSON action object."
                transcript.append({"step": step, "type": "observation", "text": observation})
                messages.append({"role": "user", "content": observation})
                if on_event:
                    on_event("observation", step, observation)
                if parse_failures >= 3:
                    return AgentResult("error", "模型连续三次输出无法解析的动作。", step, transcript)
                continue
            if action.kind == "final":
                answer = action.answer or ""
                self._record_completion(answer, transcript)
                return AgentResult("completed", answer, step, transcript)
            observation = self.registry.execute(action.tool or "", action.arguments or {})
            transcript.append(
                {
                    "step": step,
                    "type": "tool",
                    "tool": action.tool,
                    "arguments": action.arguments or {},
                    "text": observation,
                }
            )
            messages.append({"role": "user", "content": json.dumps({"kind": "tool_result", "tool": action.tool, "output": observation}, ensure_ascii=False)})
            if on_event:
                on_event("tool", step, f"{action.tool}: {observation}")
        return AgentResult("limit", f"已达到最大步数 {self.max_steps}，任务尚未确认完成。", self.max_steps, transcript)

    def _record_completion(self, answer: str, transcript: list[dict[str, Any]]) -> None:
        if not any(item.get("type") == "tool" for item in transcript):
            return
        try:
            self.memory.record("work", summarize_transcript(transcript, answer), title="Agent run completed", tags=["auto"])
        except OSError:
            pass
