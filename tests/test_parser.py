import pytest

from coding_agent.parser import ActionParseError, parse_action


def test_parses_fenced_tool_action():
    action = parse_action('```json\n{"kind":"tool","tool":"read_file","arguments":{"path":"a.py"}}\n```')
    assert action.kind == "tool"
    assert action.tool == "read_file"
    assert action.arguments == {"path": "a.py"}


def test_parses_final_action_with_trailing_text():
    action = parse_action('{"kind":"final","answer":"done"}\n')
    assert action.answer == "done"


def test_rejects_invalid_action():
    with pytest.raises(ActionParseError):
        parse_action("I changed the file")

