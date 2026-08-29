from text_tools import normalize_words


def test_empty_text():
    assert normalize_words("") == []
    assert normalize_words(" , ; ") == []


def test_unique_normalized_words():
    assert normalize_words("Agent, agent! Tools-run tests.") == ["agent", "run", "tests", "tools"]


def test_numbers_are_kept():
    assert normalize_words("V4 pro and v4 flash") == ["and", "flash", "pro", "v4"]
