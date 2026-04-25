from __future__ import annotations

from pathlib import Path

from src.run_daily import _load_company_rows, title_matches_profile
from src.scrapers import detect_job_board


def test_detect_job_board_from_url() -> None:
    assert detect_job_board("https://boards.greenhouse.io/acme") == "greenhouse"
    assert detect_job_board("https://jobs.lever.co/acme") == "lever"
    assert detect_job_board("https://jobs.ashbyhq.com/acme") == "ashby"
    assert detect_job_board("https://careers.example.com") == "generic"


def test_title_matches_profile() -> None:
    context = {"target_roles": ["Product Manager", "Senior Product Manager"]}
    assert title_matches_profile("Senior Product Manager, Platform", context) is True
    assert title_matches_profile("Backend Engineer", context) is False


def test_load_company_rows_skips_comments_and_disabled(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        (
            "company_name,careers_url,job_board,user_id,role_keywords,enabled\n"
            "# Comment,,,\n"
            "Acme,https://boards.greenhouse.io/acme,greenhouse,wife_pm,product manager,true\n"
            "Beta,https://jobs.lever.co/beta,lever,me_analytics,analytics,false\n"
        ),
        encoding="utf-8",
    )

    rows = _load_company_rows(csv_path)
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Acme"

