from pathlib import Path

from coding_agent.memory import ProjectMemoryStore, estimate_tokens, tokenize_query


def test_tokenizer_handles_chinese_and_code_identifiers():
    tokens = tokenize_query("修复 memoryRecord 和 PROJECT_MEMORY.md")
    assert "修复" in tokens
    assert "memoryrecord" in tokens
    assert "memory" in tokens
    assert "record" in tokens
    assert "project_memory" in tokens
    assert "project" in tokens
    assert "memory" in tokens


def test_bm25_search_ranks_title_and_code_matches(tmp_path: Path):
    store = ProjectMemoryStore(tmp_path)
    store.record("lessons", "Prefer bounded hot-memory injection instead of dumping full history.", title="Hot Memory")
    store.record("work", "Touched unrelated files while debugging a failing shell command.", title="Shell cleanup")
    results = store.search("hotMemory", limit=2)
    assert results[0].title == "Hot Memory"


def test_project_memory_deduplicates_near_identical_entries(tmp_path: Path):
    store = ProjectMemoryStore(tmp_path)
    first = store.record("actions", "Always run pytest after editing the agent loop.", title="Verification")
    second = store.record("actions", "Always run pytest after editing the agent loop.", title="Verification")
    assert first.id == second.id
    assert len(store.load()) == 1


def test_hot_memory_respects_token_budget(tmp_path: Path):
    store = ProjectMemoryStore(tmp_path)
    store.record("actions", "Run pytest and the offline demo before submission." * 50, title="Verify")
    hot = store.hot_memory(target_tokens=40, hard_max_tokens=80)
    assert estimate_tokens(hot) <= 80
    assert "Verify" in hot
