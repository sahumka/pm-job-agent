from __future__ import annotations

from pathlib import Path

from src.run_daily import run_daily


def test_manual_import_respects_cli_user_scope(monkeypatch, tmp_path: Path) -> None:
    inserted_user_ids: list[str] = []

    monkeypatch.setattr("src.run_daily._load_company_rows", lambda _path: [])
    monkeypatch.setattr("src.run_daily.load_linkedin_jobs_from_csv", lambda _path: [])
    monkeypatch.setattr(
        "src.run_daily.load_jobs_from_csv",
        lambda _path, default_job_board="manual": [
            {
                "user_id": "other_user",
                "company": "Example Co",
                "title": "Senior Product Manager",
                "location": "Remote US",
                "source_url": "https://example.com/jobs/1",
                "job_board": "manual",
                "description": "role details",
            }
        ],
    )
    monkeypatch.setattr(
        "src.run_daily.load_profile",
        lambda user_id=None: {
            "user_id": user_id or "default",
            "display_name": "Test User",
            "target_roles": ["Senior Product Manager"],
            "preferred_locations": ["Remote US"],
            "setup_completed": True,
            "crawl_active": True,
        },
    )
    monkeypatch.setattr(
        "src.run_daily.score_job",
        lambda _job, context: {
            "fit_score": 4.5,
            "recommendation": "Apply",
            "score_reason": "Strong fit",
            "gaps": [],
            "resume_keywords": [],
        },
    )

    def _capture_insert(payload: dict[str, object], db_path: str) -> bool:
        inserted_user_ids.append(str(payload.get("user_id")))
        return True

    monkeypatch.setattr("src.run_daily.insert_job", _capture_insert)

    summary = run_daily(
        companies_csv=str(tmp_path / "companies.csv"),
        linkedin_csv=str(tmp_path / "linkedin.csv"),
        manual_jobs_csv=str(tmp_path / "manual.csv"),
        db_path=str(tmp_path / "jobs.db"),
        user_id="shiven_analytics",
        skip_digest=True,
    )

    assert summary["manual_rows_loaded"] == 1
    assert summary["jobs_inserted"] == 1
    assert inserted_user_ids == ["shiven_analytics"]
