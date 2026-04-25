from __future__ import annotations

from src.validate_targets import suggestion_candidates


def test_suggestion_candidates_has_expected_fallbacks() -> None:
    candidates = suggestion_candidates("https://example.com/careers")
    assert candidates[0] == "https://example.com/careers"
    assert "https://example.com/jobs" in candidates
    assert "https://example.com/careers/jobs" in candidates


def test_suggestion_candidates_normalizes_missing_scheme() -> None:
    candidates = suggestion_candidates("example.com")
    assert candidates[0] == "https://example.com"

