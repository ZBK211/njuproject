from pathlib import Path

from coding_agent.tools.registry import ToolContext, ToolRegistry
from coding_agent.tools.filesystem import register_filesystem_tools
from coding_agent.tools.memory import register_memory_tools
from coding_agent.tools.shell import register_shell_tools


def make_registry(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry(ToolContext(tmp_path, command_timeout=3, approve_commands=lambda _: True))
    register_filesystem_tools(registry)
    register_shell_tools(registry)
    register_memory_tools(registry)
    return registry


def test_filesystem_tools_are_workspace_scoped(tmp_path):
    registry = make_registry(tmp_path)
    assert registry.execute("write_file", {"path": "src/a.txt", "content": "hello"}).startswith("OK:")
    assert registry.execute("read_file", {"path": "src/a.txt"}) == "hello"
    assert "src/a.txt" in registry.execute("search", {"query": "hello"})
    assert "escapes" in registry.execute("read_file", {"path": "../outside.txt"})


def test_edit_requires_expected_occurrence_count(tmp_path):
    registry = make_registry(tmp_path)
    registry.execute("write_file", {"path": "a.txt", "content": "x x"})
    result = registry.execute("edit_file", {"path": "a.txt", "old": "x", "new": "y"})
    assert "expected 1" in result
    assert registry.execute("edit_file", {"path": "a.txt", "old": "x", "new": "y", "expected_occurrences": 2}).startswith("OK:")


def test_shell_returns_exit_code(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.execute("run_command", {"command": "python -c \"print('ok')\""})
    assert "exit_code=0" in result
    assert "ok" in result


def test_shell_blocks_destructive_commands(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.execute("run_command", {"command": "git reset --hard"})
    assert result.startswith("DENIED:")


def test_memory_tools_record_and_read(tmp_path):
    registry = make_registry(tmp_path)
    recorded = registry.execute(
        "memory_record",
        {
            "section": "lessons",
            "title": "Encoding",
            "content": "Use UTF-8 output for demo scripts.",
            "tags": ["demo", "windows"],
        },
    )
    assert recorded.startswith("OK:")
    recalled = registry.execute("memory_read", {"query": "UTF-8", "limit": 3})
    assert "Encoding" in recalled
    assert "demo" in recalled
