from __future__ import annotations

from pathlib import Path

from src.scrapers.linkedin import load_linkedin_jobs_from_csv


def test_load_linkedin_jobs_from_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "linkedin_jobs.csv"
    csv_file.write_text(
        (
            "source_url,title,company,location,description,date_posted\n"
            "https://www.linkedin.com/jobs/view/1,Senior Product Manager,Acme,Remote US,Own roadmap,2026-04-24\n"
        ),
        encoding="utf-8",
    )

    rows = load_linkedin_jobs_from_csv(csv_file)
    assert len(rows) == 1
    assert rows[0]["job_board"] == "linkedin"
    assert rows[0]["company"] == "Acme"

