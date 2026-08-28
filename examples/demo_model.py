from __future__ import annotations

from coding_agent.llm import ModelResponse


class DemoModel:
    """Deterministic offline model used for repeatable demonstrations and tests."""

    def __init__(self):
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        if self.calls == 1:
            text = '{"kind":"tool","tool":"list_dir","arguments":{"path":"."}}'
        elif self.calls == 2:
            text = '{"kind":"tool","tool":"read_file","arguments":{"path":"fizzbuzz.py"}}'
        elif self.calls == 3:
            text = '{"kind":"tool","tool":"write_file","arguments":{"path":"fizzbuzz.py","content":"def fizzbuzz(n):\\n    result = []\\n    for i in range(1, n + 1):\\n        if i % 15 == 0:\\n            result.append(\\\"FizzBuzz\\\")\\n        elif i % 3 == 0:\\n            result.append(\\\"Fizz\\\")\\n        elif i % 5 == 0:\\n            result.append(\\\"Buzz\\\")\\n        else:\\n            result.append(str(i))\\n    return result\\n"}}'
        elif self.calls == 4:
            text = '{"kind":"tool","tool":"run_command","arguments":{"command":"python -m pytest -q"}}'
        else:
            text = '{"kind":"final","answer":"Implemented fizzbuzz(n) and verified it with pytest."}'
        return ModelResponse(text=text, raw={"demo_call": self.calls})
