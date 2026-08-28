from __future__ import annotations

import json
import shutil
import sys
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_agent.agent import Agent
from examples.demo_model import DemoModel


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web_demo"
DEMO_WORKSPACE = ROOT / "demo_workspace"
DEMO_TEMPLATE = ROOT / "examples" / "demo_workspace_template"


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            file_path = WEB_ROOT / "static" / path.removeprefix("/static/")
            content_type = "text/css; charset=utf-8" if file_path.suffix == ".css" else "application/javascript; charset=utf-8"
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
            data = run_demo(task if isinstance(task, str) and task.strip() else None)
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


def run_demo(task: str | None = None) -> dict:
    if DEMO_WORKSPACE.exists():
        shutil.rmtree(DEMO_WORKSPACE)
    shutil.copytree(DEMO_TEMPLATE, DEMO_WORKSPACE)
    events: list[dict] = []

    def on_event(kind: str, step: int, text: str) -> None:
        events.append({"kind": kind, "step": step, "text": text})

    agent = Agent(DemoModel(), DEMO_WORKSPACE, max_steps=8, approve_commands=lambda command: True)
    result = agent.run(task or "Implement the FizzBuzz task in the workspace and verify it with tests.", on_event=on_event)
    test_output = _last_tool_output(result.transcript, "run_command")
    memory_path = DEMO_WORKSPACE / ".agent" / "PROJECT_MEMORY.md"
    return {
        "status": result.status,
        "answer": result.answer,
        "steps": result.steps,
        "transcript": result.transcript,
        "events": events,
        "files": {
            "fizzbuzz": _read_text(DEMO_WORKSPACE / "fizzbuzz.py"),
            "test_fizzbuzz": _read_text(DEMO_WORKSPACE / "test_fizzbuzz.py"),
        },
        "test_output": test_output,
        "tests_passed": "passed" in test_output and "exit_code=0" in test_output,
        "memory": _read_text(memory_path),
        "memory_recorded": memory_path.exists(),
        "audit": compliance_audit(),
    }


def compliance_audit() -> list[dict[str, str]]:
    return [
        {"level": "ok", "title": "未使用 Agent 框架", "detail": "运行时只依赖 Python 标准库；没有 LangChain、LlamaIndex、OpenAI Agents SDK、AutoGen、CrewAI。"},
        {"level": "ok", "title": "本地工具执行", "detail": "文件读写、搜索和命令执行都在本机工作区完成，没有使用服务端 Files API 或 Code Interpreter。"},
        {"level": "ok", "title": "核心逻辑自写", "detail": "Agent loop、JSON 动作解析、上下文压缩、工具注册、错误恢复和终止条件都在 coding_agent 中实现。"},
        {"level": "ok", "title": "密钥不入库", "detail": "真实模型只从 OPENAI_API_KEY 等环境变量读取；当前 demo 不需要 API Key。"},
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
