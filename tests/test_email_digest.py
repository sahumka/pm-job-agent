from __future__ import annotations

from datetime import date
from pathlib import Path

from src.db import init_db, insert_job
from src.email_digest import fetch_jobs_for_digest, render_digest_html, save_digest_html


def test_fetch_and_render_digest(tmp_path: Path) -> None:
    db_path = tmp_path / "jobs.db"
    init_db(db_path)

    row = {
        "user_id": "wife_pm",
        "company": "Acme",
        "title": "Senior Product Manager",
        "location": "Seattle",
        "source_url": "https://example.com/jobs/1",
        "job_board": "generic",
        "description": "Roadmap and metrics ownership.",
        "date_found": date.today().isoformat(),
        "fit_score": 4.3,
        "score_reason": "Strong PM role fit.",
        "gaps": '["Needs deeper AI domain exposure"]',
        "resume_keywords": '["roadmap","metrics"]',
    }
    inserted = insert_job(row, db_path=db_path)
    assert inserted is True

    jobs, total = fetch_jobs_for_digest(db_path=str(db_path), user_id="wife_pm", limit=10)
    assert total == 1
    assert len(jobs) == 1

    html = render_digest_html(jobs=jobs, total_new_jobs=total, user_id="wife_pm")
    assert "Daily Job Digest" in html
    assert "Senior Product Manager" in html
    assert "Apply Link" in html

    output_path = tmp_path / "digest.html"
    path = save_digest_html(html, output_path=str(output_path))
    assert path.exists()

