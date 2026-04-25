from src.score_job import compact_text, score_job


def test_scoring_returns_expected_shape() -> None:
    context = {
        "target_roles": ["Senior Product Manager", "AI Product Manager"],
        "preferred_locations": ["Seattle", "Remote US"],
        "domains": ["ai", "platform"],
        "skills": ["roadmap", "metrics", "stakeholder"],
        "target_seniority": ["senior"],
        "years_experience": 5,
    }
    result = score_job(
        {
            "title": "Senior Product Manager, AI Platform",
            "description": "Own roadmap, metrics, experimentation, and stakeholder alignment.",
            "location": "Seattle, WA",
            "source_url": "https://boards.greenhouse.io/example/jobs/123",
        },
        context=context,
    )

    assert isinstance(result["fit_score"], float)
    assert result["recommendation"] in {"Apply", "Maybe", "Skip"}
    assert isinstance(result["gaps"], list)
    assert isinstance(result["resume_keywords"], list)


def test_compact_text_truncates() -> None:
    long_text = "x" * 5000
    value = compact_text(long_text, max_len=100)
    assert len(value) == 100
    assert value.endswith("...")
