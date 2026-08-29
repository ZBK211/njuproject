from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PACKAGES = {
    "langchain",
    "llamaindex",
    "llama_index",
    "autogen",
    "crewai",
    "openai_agents",
    "claude_agent",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]
ENV_SECRET_RE = re.compile(r"(DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*=\s*(.+)", re.IGNORECASE)
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "tmp", "demo_workspace", "submission"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".html", ".css", ".js", ".example", ""}


def main() -> int:
    checks = [
        ("README.txt exists and is <= 1000 chars", check_readme),
        ("Git remote is configured", check_git_remote),
        ("Core agent files exist", check_core_files),
        ("No forbidden agent framework dependency/import in runtime code", check_forbidden_runtime_code),
        ("No obvious API key committed", check_no_secrets),
        ("DeepSeek demo defaults to V4", check_deepseek_v4),
        ("Tests pass", check_tests),
    ]
    failed = 0
    for title, check in checks:
        ok, detail = check()
        marker = "OK" if ok else "FAIL"
        print(f"[{marker}] {title}: {detail}")
        failed += 0 if ok else 1
    return 1 if failed else 0


def check_readme() -> tuple[bool, str]:
    path = ROOT / "README.txt"
    if not path.is_file():
        return False, "missing"
    text = path.read_text(encoding="utf-8")
    if len(text) > 1000:
        return False, f"{len(text)} chars"
    if "https://github.com/ZBK211/njuproject" not in text:
        return False, "repository URL missing"
    return True, f"{len(text)} chars"


def check_git_remote() -> tuple[bool, str]:
    result = subprocess.run(["git", "remote", "-v"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        return False, result.stderr.strip() or "git remote failed"
    has_repo = "ZBK211/njuproject" in result.stdout
    return has_repo, "ZBK211/njuproject" if has_repo else "expected remote not found"


def check_core_files() -> tuple[bool, str]:
    required = [
        "coding_agent/agent.py",
        "coding_agent/parser.py",
        "coding_agent/tools/registry.py",
        "coding_agent/tools/filesystem.py",
        "coding_agent/tools/shell.py",
        "coding_agent/llm.py",
        "scripts/run_deepseek_demo.py",
        "scripts/demo_server.py",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    return not missing, "all present" if not missing else ", ".join(missing)


def check_forbidden_runtime_code() -> tuple[bool, str]:
    offenders: list[str] = []
    for path in _iter_text_files({".py", ".toml", ".txt"}):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if path.suffix == ".py":
            import_lines = "\n".join(line for line in text.splitlines() if line.startswith(("import ", "from ")))
            for package in FORBIDDEN_PACKAGES:
                if re.search(rf"(^|\W){re.escape(package)}(\W|$)", import_lines):
                    offenders.append(str(path.relative_to(ROOT)))
        if path.name in {"requirements.txt", "pyproject.toml"}:
            for package in FORBIDDEN_PACKAGES:
                if re.search(rf"(^|\W){re.escape(package)}(\W|$)", text):
                    offenders.append(str(path.relative_to(ROOT)))
    return not offenders, "clean" if not offenders else ", ".join(sorted(set(offenders)))


def check_no_secrets() -> tuple[bool, str]:
    offenders: list[str] = []
    for path in _iter_text_files(TEXT_SUFFIXES):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(str(path.relative_to(ROOT)))
                break
        for line in text.splitlines():
            match = ENV_SECRET_RE.search(line)
            if not match:
                continue
            value = match.group(2).strip().strip("\"'")
            if value in {"", "...", "replace-me"}:
                continue
            offenders.append(str(path.relative_to(ROOT)))
            break
    return not offenders, "clean" if not offenders else ", ".join(sorted(set(offenders)))


def check_deepseek_v4() -> tuple[bool, str]:
    files = [ROOT / "scripts" / "demo_server.py", ROOT / "scripts" / "run_deepseek_demo.py", ROOT / "web_demo" / "index.html"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files if path.exists())
    ok = "deepseek-v4-flash" in text and "deepseek-chat" not in text
    return ok, "deepseek-v4-flash" if ok else "V4 default not found or old model remains"


def check_tests() -> tuple[bool, str]:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        return False, (result.stdout + result.stderr).strip()[-500:]
    return True, result.stdout.strip().splitlines()[-1]


def _iter_text_files(suffixes: set[str]):
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path


if __name__ == "__main__":
    raise SystemExit(main())
