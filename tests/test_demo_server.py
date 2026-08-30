from scripts.demo_server import _select_test_file, run_demo


def test_web_demo_uses_isolated_workspaces():
    first = run_demo(mode="offline")
    second = run_demo(mode="offline")
    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["workspace"] != second["workspace"]
    assert "web_runs" in first["workspace"]
    assert "web_runs" in second["workspace"]


def test_web_demo_detects_pytest_target_with_nonstandard_name():
    files = {
        "palindrome.py": "def is_palindrome(text):\n    return True\n",
        "pytest_model.py": "from palindrome import is_palindrome\n\n\ndef test_basic():\n    assert is_palindrome('aba')\n",
    }
    transcript = [
        {
            "type": "tool",
            "tool": "run_command",
            "arguments": {"command": "python -m pytest pytest_model.py -v"},
            "text": "exit_code=0\n1 passed",
        }
    ]
    assert _select_test_file(files, "", transcript) == "pytest_model.py"
