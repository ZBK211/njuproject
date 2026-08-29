from scripts.demo_server import run_demo


def test_web_demo_uses_isolated_workspaces():
    first = run_demo(mode="offline")
    second = run_demo(mode="offline")
    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["workspace"] != second["workspace"]
    assert "web_runs" in first["workspace"]
    assert "web_runs" in second["workspace"]
