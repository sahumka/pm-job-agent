from src.dedupe import dedupe_key, normalize_text


def test_normalize_text_trims_and_lowercases() -> None:
    assert normalize_text("  Senior   Product MANAGER ") == "senior product manager"


def test_dedupe_key_normalizes_values() -> None:
    key = dedupe_key("Acme", "Product Manager", "Seattle")
    assert key == "acme|product manager|seattle"
