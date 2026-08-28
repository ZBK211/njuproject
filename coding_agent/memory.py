from __future__ import annotations

import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECTIONS = {
    "work": "Work Log",
    "lessons": "Lessons",
    "actions": "Action Guide",
    "note": "Notes",
}

SECTION_WEIGHTS = {
    "actions": 4.0,
    "lessons": 3.5,
    "work": 2.0,
    "note": 0.5,
}

BM25_K1 = 1.5
BM25_B = 0.75
TITLE_BOOST = 2.5
EXACT_PHRASE_BOOST = 2.0


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    section: str
    title: str
    content: str
    created_at: float
    tags: list[str]


class ProjectMemoryStore:
    """Local project memory with a structured store and readable projection."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.agent_dir = self.root / ".agent"
        self.store_path = self.agent_dir / "memory.json"
        self.projection_path = self.agent_dir / "PROJECT_MEMORY.md"

    def load(self) -> list[MemoryEntry]:
        if not self.store_path.exists():
            return []
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            backup = self.store_path.with_suffix(f".corrupt.{int(time.time())}.json")
            try:
                self.store_path.replace(backup)
            except OSError:
                pass
            return []
        entries = raw.get("entries", []) if isinstance(raw, dict) else []
        result: list[MemoryEntry] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            section = item.get("section")
            content = item.get("content")
            if section not in SECTIONS or not isinstance(content, str) or not content.strip():
                continue
            title = item.get("title", "")
            tags = item.get("tags", [])
            result.append(
                MemoryEntry(
                    id=str(item.get("id") or uuid.uuid4().hex[:12]),
                    section=section,
                    title=title if isinstance(title, str) else "",
                    content=content.strip(),
                    created_at=float(item.get("created_at") or time.time()),
                    tags=[tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else [],
                )
            )
        return result

    def record(self, section: str, content: str, *, title: str = "", tags: list[str] | None = None) -> MemoryEntry:
        if section not in SECTIONS:
            raise ValueError(f"section must be one of {', '.join(SECTIONS)}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        entries = self.load()
        normalized = content.strip()
        clean_title = title.strip()[:120] if isinstance(title, str) else ""
        duplicate = self.find_near_duplicate(section, normalized, title=clean_title)
        if duplicate is not None:
            return duplicate
        entry = MemoryEntry(
            id=uuid.uuid4().hex[:12],
            section=section,
            title=clean_title,
            content=normalized,
            created_at=time.time(),
            tags=_clean_tags(tags or []),
        )
        entries.append(entry)
        self._save(entries)
        return entry

    def search(self, query: str = "", *, section: str | None = None, limit: int = 8) -> list[MemoryEntry]:
        entries = [entry for entry in self.load() if section in (None, "", entry.section)]
        limit = max(1, min(int(limit), 30))
        if not query.strip():
            return sorted(entries, key=lambda entry: entry.created_at, reverse=True)[:limit]
        return [ranked.entry for ranked in rank_memory(entries, query)[:limit]]

    def find_near_duplicate(self, section: str, content: str, *, title: str = "") -> MemoryEntry | None:
        probe_tokens = set(tokenize_query(f"{title} {content}"))
        for entry in self.load():
            if entry.section != section:
                continue
            existing = set(tokenize_query(f"{entry.title} {entry.content}"))
            if not probe_tokens and not existing:
                continue
            overlap = len(probe_tokens & existing) / max(1, len(probe_tokens | existing))
            same_title = bool(title) and title == entry.title
            if (same_title and overlap >= 0.80) or overlap >= 0.92:
                return entry
        return None

    def hot_memory(self, *, target_tokens: int = 900, hard_max_tokens: int = 1200) -> str:
        entries = self.search(limit=12)
        if not entries:
            return ""
        ranked = sorted(
            (entry for entry in entries if entry.section != "note"),
            key=lambda entry: (SECTION_WEIGHTS[entry.section], entry.created_at),
            reverse=True,
        )
        lines = ["Project memory:"]
        for entry in ranked:
            prefix = SECTIONS[entry.section]
            title = f"{entry.title}: " if entry.title else ""
            line = f"- [{prefix}] {title}{entry.content}"
            probe = "\n".join([*lines, line])
            if estimate_tokens(probe) > hard_max_tokens:
                if len(lines) == 1:
                    lines.append(_fit_line(line, lines[0], hard_max_tokens))
                break
            lines.append(line)
            if estimate_tokens(probe) >= target_tokens:
                break
        return "\n".join(lines)

    def render(self) -> str:
        lines = [
            "# Project Memory",
            "",
            "> Generated by ForgeAgent from .agent/memory.json. It is local project memory, not a secret store.",
            "",
        ]
        entries = self.load()
        for section, label in SECTIONS.items():
            group = [entry for entry in entries if entry.section == section]
            if not group:
                continue
            lines.extend([f"## {label}", ""])
            for entry in sorted(group, key=lambda item: item.created_at):
                title = f"{entry.title} - " if entry.title else ""
                lines.append(f"- `{entry.id}` {title}{entry.content}")
            lines.append("")
        if not entries:
            lines.extend(["No memory recorded yet.", ""])
        return "\n".join(lines)

    def _save(self, entries: list[MemoryEntry]) -> None:
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "entries": [
                {
                    "id": entry.id,
                    "section": entry.section,
                    "title": entry.title,
                    "content": entry.content,
                    "created_at": entry.created_at,
                    "tags": entry.tags,
                }
                for entry in entries
            ],
        }
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.store_path)
        self.projection_path.write_text(self.render(), encoding="utf-8")


def format_entries(entries: list[MemoryEntry]) -> str:
    if not entries:
        return "(no matching memory)"
    lines = []
    for entry in entries:
        title = f"{entry.title} - " if entry.title else ""
        tags = f" tags={','.join(entry.tags)}" if entry.tags else ""
        lines.append(f"- {entry.id} [{entry.section}]{tags} {title}{entry.content}")
    return "\n".join(lines)


def summarize_transcript(transcript: list[dict[str, Any]], answer: str) -> str:
    tools = [item.get("tool", "") for item in transcript if item.get("type") == "tool"]
    unique_tools = ", ".join(dict.fromkeys(tool for tool in tools if tool))
    if unique_tools:
        return f"Completed run using tools: {unique_tools}. Result: {answer.strip()}"
    return f"Completed run. Result: {answer.strip()}"


@dataclass(frozen=True)
class RankedMemory:
    entry: MemoryEntry
    score: float


def rank_memory(entries: list[MemoryEntry], query: str, *, now: float | None = None) -> list[RankedMemory]:
    query_terms = tokenize_query(query)
    if not query_terms:
        return []
    now = now or time.time()
    body_docs = [tokenize_document(entry.content + " " + " ".join(entry.tags)) for entry in entries]
    title_docs = [tokenize_document(entry.title) for entry in entries]
    avg_body = sum(len(doc) for doc in body_docs) / max(1, len(body_docs))
    avg_title = sum(len(doc) for doc in title_docs) / max(1, len(title_docs))
    body_df = _document_frequency(body_docs)
    title_df = _document_frequency(title_docs)
    ranked = []
    phrase = query.lower().strip()
    for index, entry in enumerate(entries):
        body_score = _bm25(body_docs[index], query_terms, body_df, avg_body, len(entries))
        title_score = _bm25(title_docs[index], query_terms, title_df, avg_title, len(entries))
        if body_score == 0 and title_score == 0:
            continue
        score = body_score + TITLE_BOOST * title_score
        if phrase and phrase in f"{entry.title} {entry.content}".lower():
            score += EXACT_PHRASE_BOOST
        score += SECTION_WEIGHTS[entry.section] * 0.1
        score += _recency_boost(entry.created_at, now) * 0.5
        ranked.append(RankedMemory(entry=entry, score=score))
    return sorted(ranked, key=lambda item: (item.score, item.entry.created_at), reverse=True)


def tokenize_document(text: str) -> list[str]:
    return _tokenize(text, dedupe=False)


def tokenize_query(text: str) -> list[str]:
    return _tokenize(text, dedupe=True)


def estimate_tokens(text: str) -> int:
    cjk = 0
    other = 0
    for char in text:
        if _is_cjk(ord(char)):
            cjk += 1
        else:
            other += 1
    return math.ceil(cjk + other / 4)


def _tokenize(text: str, *, dedupe: bool) -> list[str]:
    tokens: list[str] = []
    cjk_run: list[str] = []
    latin_run: list[str] = []

    def flush_cjk() -> None:
        if not cjk_run:
            return
        if len(cjk_run) == 1:
            tokens.append(cjk_run[0])
        else:
            for index in range(len(cjk_run) - 1):
                tokens.append(cjk_run[index] + cjk_run[index + 1])
            for index in range(len(cjk_run) - 2):
                tokens.append(cjk_run[index] + cjk_run[index + 1] + cjk_run[index + 2])
        cjk_run.clear()

    def flush_latin() -> None:
        if not latin_run:
            return
        raw = "".join(latin_run)
        for part in re.split(r"[^A-Za-z0-9_]+", raw):
            if not part:
                continue
            tokens.append(part.lower())
            pieces = [piece for piece in part.lower().split("_") if piece]
            if len(pieces) > 1:
                tokens.extend(pieces)
            camel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", part).split()
            if len(camel) > 1:
                tokens.extend(piece.lower() for piece in camel if piece)
        latin_run.clear()

    for char in text:
        if _is_cjk(ord(char)):
            flush_latin()
            cjk_run.append(char)
        else:
            flush_cjk()
            latin_run.append(char)
    flush_latin()
    flush_cjk()
    return list(dict.fromkeys(tokens)) if dedupe else tokens


def _is_cjk(codepoint: int) -> bool:
    return (
        0x3000 <= codepoint <= 0x303F
        or 0x3040 <= codepoint <= 0x30FF
        or 0x3400 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0xFF00 <= codepoint <= 0xFFEF
        or 0xAC00 <= codepoint <= 0xD7AF
    )


def _document_frequency(docs: list[list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            counts[term] = counts.get(term, 0) + 1
    return counts


def _bm25(doc: list[str], query_terms: list[str], doc_freq: dict[str, int], avg_length: float, doc_count: int) -> float:
    if not doc:
        return 0.0
    term_counts: dict[str, int] = {}
    for term in doc:
        term_counts[term] = term_counts.get(term, 0) + 1
    score = 0.0
    for term in query_terms:
        tf = term_counts.get(term, 0)
        if tf == 0:
            continue
        df = doc_freq.get(term, 0)
        idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
        denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * len(doc) / max(1, avg_length))
        score += idf * (tf * (BM25_K1 + 1) / denominator)
    return score


def _recency_boost(created_at: float, now: float) -> float:
    age_days = max(0.0, now - created_at) / 86_400
    return 1.0 / (1.0 + age_days / 30.0)


def _fit_line(line: str, header: str, hard_max_tokens: int) -> str:
    suffix = "...(truncated)"
    budget_line = line
    while budget_line and estimate_tokens(f"{header}\n{budget_line}{suffix}") > hard_max_tokens:
        budget_line = budget_line[:-16]
    return budget_line.rstrip() + suffix


def _clean_tags(tags: list[str]) -> list[str]:
    seen = set()
    result = []
    for tag in tags:
        clean = tag.strip()[:40]
        if clean and clean not in seen:
            result.append(clean)
            seen.add(clean)
    return result[:8]
