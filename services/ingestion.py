from __future__ import annotations

from typing import Any

from src.extract_job import run_manual_ingest
from src.run_daily import run_daily


def run_job_ingestion(
    db_path: str,
    companies_csv: str,
    linkedin_csv: str,
    manual_jobs_csv: str,
    user_id: str | None,
) -> dict[str, Any]:
    return run_daily(
        companies_csv=companies_csv,
        linkedin_csv=linkedin_csv,
        manual_jobs_csv=manual_jobs_csv,
        db_path=db_path,
        user_id=user_id,
        timeout=20,
        output_digest="outputs/daily_digest.html",
        skip_digest=False,
    )


def ingest_single_job_url(url: str, db_path: str, user_id: str | None) -> dict[str, Any]:
    return run_manual_ingest(url=url, db_path=db_path, user_id=user_id)
