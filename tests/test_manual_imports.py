from __future__ import annotations

from pathlib import Path

from src.scrapers.manual_imports import load_jobs_from_csv


def test_load_jobs_from_csv_supports_multiple_boards(tmp_path: Path) -> None:
    csv_file = tmp_path / "manual_jobs.csv"
    csv_file.write_text(
        (
            "source_url,title,company,location,description,date_posted,job_board,user_id\n"
            "https://wellfound.com/jobs/1,Product Analytics Manager,Acme,Remote US,Own analytics,2026-04-24,wellfound,me_analytics\n"
            "https://builtin.com/job/2,Data Product Manager,Beta,Seattle,Build data products,2026-04-24,builtin,\n"
        ),
        encoding="utf-8",
    )

    rows = load_jobs_from_csv(csv_file)
    assert len(rows) == 2
    assert rows[0]["job_board"] == "wellfound"
    assert rows[0]["user_id"] == "me_analytics"
    assert rows[1]["job_board"] == "builtin"

