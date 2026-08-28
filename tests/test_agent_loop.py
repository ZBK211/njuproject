from pathlib import Path

from coding_agent.agent import Agent
from coding_agent.llm import ModelResponse


class ScriptedModel:
    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, messages):
        return ModelResponse(next(self.responses), raw={})


def test_agent_executes_tools_and_stops_on_final(tmp_path: Path):
    model = ScriptedModel([
        '{"kind":"tool","tool":"write_file","arguments":{"path":"answer.txt","content":"42"}}',
        '{"kind":"tool","tool":"read_file","arguments":{"path":"answer.txt"}}',
        '{"kind":"final","answer":"verified"}',
    ])
    result = Agent(model, tmp_path, max_steps=4, approve_commands=lambda _: True).run("make answer.txt")
    assert result.status == "completed"
    assert result.steps == 3
    assert (tmp_path / "answer.txt").read_text(encoding="utf-8") == "42"


def test_agent_recovers_from_bad_json(tmp_path: Path):
    model = ScriptedModel(["not json", '{"kind":"final","answer":"recovered"}'])
    result = Agent(model, tmp_path, max_steps=3).run("test")
    assert result.status == "completed"
    assert result.steps == 2


def test_agent_enforces_step_limit(tmp_path: Path):
    model = ScriptedModel(['{"kind":"tool","tool":"list_dir","arguments":{"path":"."}}'] * 2)
    result = Agent(model, tmp_path, max_steps=2).run("loop")
    assert result.status == "limit"


def test_agent_compacts_large_context(tmp_path: Path):
    seen_messages = []

    class InspectingModel:
        def __init__(self):
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            seen_messages.append(messages)
            if self.calls == 1:
                return ModelResponse('{"kind":"tool","tool":"write_file","arguments":{"path":"big.txt","content":"'
                                     + ("x" * 120)
                                     + '"}}', raw={})
            return ModelResponse('{"kind":"final","answer":"done"}', raw={})

    result = Agent(InspectingModel(), tmp_path, max_steps=3, max_context_chars=220).run("make a large file")
    assert result.status == "completed"
    assert any("context_note" in message["content"] for message in seen_messages[-1])


def test_agent_auto_records_completion_and_injects_memory(tmp_path: Path):
    model = ScriptedModel([
        '{"kind":"tool","tool":"write_file","arguments":{"path":"answer.txt","content":"42"}}',
        '{"kind":"final","answer":"verified answer file"}',
    ])
    result = Agent(model, tmp_path, max_steps=3).run("write answer")
    assert result.status == "completed"
    memory_file = tmp_path / ".agent" / "memory.json"
    assert memory_file.is_file()
    assert "verified answer file" in memory_file.read_text(encoding="utf-8")

    agent = Agent(ScriptedModel(['{"kind":"final","answer":"done"}']), tmp_path)
    assert "Project memory:" in agent._system_prompt()
