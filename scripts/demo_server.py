from __future__ import annotations

import json
import os
import shutil
import sys
import argparse
import difflib
import uuid
from time import perf_counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_agent.agent import Agent
from coding_agent.config import Settings
from coding_agent.llm import OpenAICompatibleModel
from examples.demo_model import DemoModel, TextToolsDemoModel


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web_demo"
DEMO_WORKSPACE_ROOT = ROOT / "demo_workspace" / "web_runs"
DEMO_TEMPLATES = {
    "scratch": {
        "path": None,
        "task": "Create a Python solution for the requested programming task, add useful pytest tests, and verify it locally.",
        "source": "",
        "test": "",
        "offline_model": DemoModel,
    },
    "fizzbuzz": {
        "path": ROOT / "examples" / "demo_workspace_template",
        "task": "Implement the FizzBuzz task in the workspace and verify it with tests.",
        "source": "fizzbuzz.py",
        "test": "test_fizzbuzz.py",
        "offline_model": DemoModel,
    },
    "text_tools": {
        "path": ROOT / "examples" / "text_tools_workspace_template",
        "task": "Implement normalize_words(text) in text_tools.py and verify it with tests.",
        "source": "text_tools.py",
        "test": "test_text_tools.py",
        "offline_model": TextToolsDemoModel,
    },
}


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/config":
            self._send_json(
                {
                    "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")),
                    "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                    "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                }
            )
            return
        if path.startswith("/static/"):
            file_path = WEB_ROOT / "static" / path.removeprefix("/static/")
            content_type = "text/css; charset=utf-8" if file_path.suffix == ".css" else "application/javascript; charset=utf-8"
            self._send_file(file_path, content_type)
            return
        if path.startswith("/assets/"):
            file_path = WEB_ROOT / "assets" / path.removeprefix("/assets/")
            content_type = "image/svg+xml; charset=utf-8" if file_path.suffix == ".svg" else "image/png"
            self._send_file(file_path, content_type)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            task = payload.get("task") if isinstance(payload, dict) else None
            mode = payload.get("mode") if isinstance(payload, dict) else None
            provider = payload.get("provider") if isinstance(payload, dict) else None
            template = payload.get("template") if isinstance(payload, dict) else None
            data = run_demo(
                task if isinstance(task, str) and task.strip() else None,
                mode=mode if isinstance(mode, str) else "deepseek",
                provider=provider if isinstance(provider, dict) else {},
                template=template if isinstance(template, str) else "scratch",
            )
            self._send_json(data)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict, *, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_demo(task: str | None = None, *, mode: str = "offline", provider: dict | None = None, template: str = "fizzbuzz") -> dict:
    started = perf_counter()
    spec = DEMO_TEMPLATES.get(template, DEMO_TEMPLATES["scratch"])
    DEMO_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    workspace = DEMO_WORKSPACE_ROOT / run_id
    if spec["path"] is None:
        workspace.mkdir(parents=True)
    else:
        shutil.copytree(spec["path"], workspace, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    before_files = _snapshot_workspace(workspace)
    events: list[dict] = []

    def on_event(kind: str, step: int, text: str) -> None:
        events.append({"kind": kind, "step": step, "text": text})

    model = _make_model(mode, provider or {}, spec)
    agent = Agent(model, workspace, max_steps=16, approve_commands=lambda command: True)
    result = agent.run(task or str(spec["task"]), on_event=on_event)
    test_output = _last_tool_output(result.transcript, "run_command")
    memory_path = workspace / ".agent" / "PROJECT_MEMORY.md"
    after_files = _snapshot_workspace(workspace)
    primary_file = _select_primary_file(after_files, before_files, str(spec["source"]))
    test_file = _select_test_file(after_files, str(spec["test"]))
    return {
        "status": result.status,
        "answer": result.answer,
        "run_id": run_id,
        "template": template if template in DEMO_TEMPLATES else "scratch",
        "mode": mode if mode == "deepseek" else "offline",
        "model": getattr(model, "settings", None).model if hasattr(model, "settings") else "DemoModel",
        "workspace": str(workspace),
        "duration_ms": round((perf_counter() - started) * 1000),
        "steps": result.steps,
        "transcript": result.transcript,
        "tool_calls": _tool_calls(result.transcript),
        "events": events,
        "changed_files": _changed_files(before_files, after_files),
        "primary_file": primary_file,
        "test_file": test_file,
        "files": {
            "source": after_files.get(primary_file, "") if primary_file else "",
            "test": after_files.get(test_file, "") if test_file else "",
        },
        "file_diff": _workspace_diff(before_files, after_files),
        "test_output": test_output,
        "tests_passed": "passed" in test_output and "exit_code=0" in test_output,
        "memory": _read_text(memory_path),
        "memory_recorded": memory_path.exists(),
        "audit": compliance_audit(),
    }


def _make_model(mode: str, provider: dict, spec: dict):
    if mode != "deepseek":
        return spec["offline_model"]()
    api_key = str(provider.get("api_key") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "")
    if not api_key:
        raise ValueError("DeepSeek API key 未配置：请在密码框输入，或在启动服务前设置 DEEPSEEK_API_KEY。")
    base_url = str(provider.get("base_url") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    model = str(provider.get("model") or os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash")
    return OpenAICompatibleModel(Settings(api_key=api_key, base_url=base_url, model=model, timeout_seconds=30))


def _tool_calls(transcript: list[dict]) -> list[dict]:
    calls = []
    for item in transcript:
        if item.get("type") != "tool":
            continue
        text = str(item.get("text", ""))
        arguments = item.get("arguments", {})
        calls.append(
            {
                "step": item.get("step"),
                "tool": item.get("tool"),
                "arguments": arguments,
                "summary": _summarize_tool(str(item.get("tool", "")), text, arguments if isinstance(arguments, dict) else {}),
                "output": text,
            }
        )
    return calls


def _summarize_tool(tool: str, output: str, arguments: dict) -> str:
    path = arguments.get("path")
    command = arguments.get("command")
    if tool == "list_dir":
        return f"列出 {path or '工作区'}，让模型先确认可操作文件。"
    if tool == "read_file":
        return f"读取 {path or '文件'}，把源码或测试内容放回模型上下文。"
    if tool == "write_file":
        return f"把模型生成的完整内容写入 {path or '文件'}。"
    if tool == "edit_file":
        return f"按精确匹配修改 {path or '文件'}，避免误改其它内容。"
    if tool == "run_command":
        return f"在本地工作区执行 {command or '命令'}，用真实结果约束下一步。"
    if tool == "memory_record":
        return "写入项目记忆，供后续会话召回。"
    if tool == "memory_read":
        return "检索项目记忆，作为本轮上下文。"
    return output.splitlines()[0][:120] if output else "本地工具已执行。"


def compliance_audit() -> list[dict[str, str]]:
    return [
        {"level": "ok", "title": "未使用 Agent 框架", "detail": "运行时只依赖 Python 标准库；没有 LangChain、LlamaIndex、OpenAI Agents SDK、AutoGen、CrewAI。"},
        {"level": "ok", "title": "本地工具执行", "detail": "文件读写、搜索和命令执行都在本机工作区完成，没有使用服务端 Files API 或 Code Interpreter。"},
        {"level": "ok", "title": "核心逻辑自写", "detail": "Agent loop、JSON 动作解析、上下文压缩、工具注册、错误恢复和终止条件都在 coding_agent 中实现。"},
        {"level": "ok", "title": "密钥不入库", "detail": "真实模型只从运行时输入或 DEEPSEEK_API_KEY 等环境变量读取；离线 demo 不需要 API Key。"},
        {"level": "ok", "title": "安全边界", "detail": "路径经过工作区限制；shell 有超时、输出截断和危险命令拦截。"},
        {"level": "warn", "title": "视频仍需本人录制", "detail": "脚本可检查 README.txt 和 MP4，但最终 2 分钟视频需要用本页面实际录制。"},
    ]


def _last_tool_output(transcript: list[dict], tool: str) -> str:
    for item in reversed(transcript):
        if item.get("type") == "tool" and item.get("tool") == tool:
            return str(item.get("text", ""))
    return ""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _unified_diff(before: str, after: str, fromfile: str, tofile: str) -> str:
    if before == after:
        return "(no file changes)"
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def _snapshot_workspace(workspace: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or _hidden_or_generated(path, workspace):
            continue
        try:
            files[path.relative_to(workspace).as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return files


def _hidden_or_generated(path: Path, workspace: Path) -> bool:
    relative_parts = path.relative_to(workspace).parts
    blocked = {".git", ".agent", "__pycache__", ".pytest_cache"}
    if any(part in blocked for part in relative_parts):
        return True
    return path.suffix in {".pyc", ".pyo"}


def _changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    names = sorted(set(before) | set(after))
    return [name for name in names if before.get(name) != after.get(name)]


def _select_primary_file(after: dict[str, str], before: dict[str, str], preferred: str) -> str:
    if preferred and preferred in after:
        return preferred
    changed = _changed_files(before, after)
    candidates = [name for name in changed if name.endswith(".py") and not Path(name).name.startswith("test_")]
    if candidates:
        return candidates[0]
    py_files = [name for name in after if name.endswith(".py") and not Path(name).name.startswith("test_")]
    return py_files[0] if py_files else (changed[0] if changed else "")


def _select_test_file(after: dict[str, str], preferred: str) -> str:
    if preferred and preferred in after:
        return preferred
    tests = [name for name in after if Path(name).name.startswith("test_") and name.endswith(".py")]
    return tests[0] if tests else ""


def _workspace_diff(before: dict[str, str], after: dict[str, str]) -> str:
    parts = []
    for name in sorted(set(before) | set(after)):
        if before.get(name) == after.get(name):
            continue
        parts.append(_unified_diff(before.get(name, ""), after.get(name, ""), f"before/{name}", f"after/{name}"))
    return "\n".join(part for part in parts if part).strip() or "(no file changes)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ForgeAgent web demo.")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    print(f"ForgeAgent demo: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo server stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
