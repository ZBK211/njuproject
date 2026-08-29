import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from coding_agent.config import Settings
from coding_agent.llm import LLMError, OpenAICompatibleModel


class ChatHandler(BaseHTTPRequestHandler):
    requests = []
    status = 200
    payload = {"choices": [{"message": {"content": "{\"kind\":\"final\",\"answer\":\"ok\"}"}}]}

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        ChatHandler.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
        body = json.dumps(ChatHandler.payload).encode("utf-8")
        self.send_response(ChatHandler.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def chat_server():
    ChatHandler.requests = []
    ChatHandler.status = 200
    ChatHandler.payload = {"choices": [{"message": {"content": "{\"kind\":\"final\",\"answer\":\"ok\"}"}}]}
    server = HTTPServer(("127.0.0.1", 0), ChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_openai_compatible_model_posts_chat_completion(chat_server):
    url = f"http://127.0.0.1:{chat_server.server_port}/v1"
    model = OpenAICompatibleModel(Settings(api_key="test-key", base_url=url, model="test-model", timeout_seconds=3))
    response = model.complete([{"role": "user", "content": "hello"}])
    assert response.text == '{"kind":"final","answer":"ok"}'
    assert ChatHandler.requests[0]["model"] == "test-model"
    assert ChatHandler.requests[0]["messages"][0]["content"] == "hello"


def test_openai_compatible_model_rejects_missing_content(chat_server):
    ChatHandler.payload = {"choices": [{"message": {}}]}
    url = f"http://127.0.0.1:{chat_server.server_port}/v1"
    model = OpenAICompatibleModel(Settings(api_key="test-key", base_url=url, model="test-model", timeout_seconds=3))
    with pytest.raises(LLMError, match="no choices"):
        model.complete([{"role": "user", "content": "hello"}])


def test_deepseek_settings_default_to_v4(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    settings = Settings.from_deepseek_env()
    assert settings.api_key == "test-key"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.model == "deepseek-v4-flash"
