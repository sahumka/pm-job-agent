from __future__ import annotations

from pathlib import Path
from typing import Any

from src.scrapers.manual_imports import load_jobs_from_csv


def load_linkedin_jobs_from_csv(csv_path: str | Path) -> list[dict[str, str]]:
    """
    Load LinkedIn jobs from a user-maintained CSV.

    Expected columns (flexible):
    - source_url (or url/link)
    - title
    - company
    - location
    - description (optional)
    - date_posted (optional, YYYY-MM-DD preferred)
    """
    jobs = load_jobs_from_csv(csv_path, default_job_board="linkedin")
    for job in jobs:
        job["job_board"] = "linkedin"
    return jobs


def scrape_linkedin_jobs(*_: Any, **__: Any) -> list[dict[str, str]]:
    """
    Placeholder online scraper intentionally returns no data.

    We avoid automated LinkedIn scraping and rely on user-export/import flows to
    stay compliant and local-first.
    """
    return []
