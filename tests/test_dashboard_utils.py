from __future__ import annotations

from datetime import date

from src.dashboard_utils import parse_json_list, split_csv_string, suggest_keywords_from_sample_jds
from src.dashboard_utils import follow_up_queue, funnel_metrics


def test_split_csv_string() -> None:
    assert split_csv_string("a, b, c") == ["a", "b", "c"]
    assert split_csv_string(" , ") == []


def test_parse_json_list() -> None:
    assert parse_json_list('["x","y"]') == ["x", "y"]
    assert parse_json_list("not-json") == []


def test_suggest_keywords_from_sample_jds() -> None:
    text = (
        "We need product strategy and product roadmap experience. "
        "Strong stakeholder management and metrics ownership required. "
        "Product roadmap and metrics work are core."
    )
    out = suggest_keywords_from_sample_jds(text, top_n=8)
    assert "product roadmap" in out
    assert "metrics" in out


def test_funnel_metrics() -> None:
    rows = [
        {"status": "New"},
        {"status": "Interested"},
        {"status": "Applied"},
        {"status": "Interview"},
        {"status": "Offer"},
    ]
    metrics = funnel_metrics(rows)
    assert metrics["total"] == 5
    assert metrics["offer"] == 1
    assert metrics["apply_rate_pct"] > 0


def test_follow_up_queue() -> None:
    today = date(2026, 4, 24)
    rows = [
        {
            "id": 1,
            "status": "Interested",
            "title": "PM",
            "company": "A",
            "updated_at": "2026-04-10",
            "created_at": "2026-04-10",
            "fit_score": 4.0,
        },
        {
            "id": 2,
            "status": "Applied",
            "title": "Analyst",
            "company": "B",
            "applied_date": "2026-04-01",
            "updated_at": "2026-04-01",
            "fit_score": 4.1,
        },
        {
            "id": 3,
            "status": "Interview",
            "title": "Finance",
            "company": "C",
            "follow_up_date": "2026-04-20",
            "fit_score": 4.3,
        },
    ]
    queue = follow_up_queue(rows, today=today)
    assert len(queue) == 3
