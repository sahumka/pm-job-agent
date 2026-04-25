from __future__ import annotations

import csv
from pathlib import Path


def _clean(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    return " ".join(str(value).split()).strip() or fallback


def load_jobs_from_csv(csv_path: str | Path, default_job_board: str = "manual") -> list[dict[str, str]]:
    """
    Load jobs from a user-maintained CSV.

    Expected columns (flexible):
    - source_url (or url/link)
    - title
    - company
    - location
    - description (optional)
    - date_posted (optional, YYYY-MM-DD preferred)
    - job_board (optional; e.g. linkedin/wellfound/builtin)
    - user_id (optional; route this row to one profile)
    """
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        return []

    jobs: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {str(k).strip().lower(): str(v or "").strip() for k, v in raw.items()}
            if row.get("source_url", "").startswith("#"):
                continue

            source_url = _clean(row.get("source_url") or row.get("url") or row.get("link"), "")
            if not source_url:
                continue

            jobs.append(
                {
                    "company": _clean(row.get("company"), "Unknown Company"),
                    "title": _clean(row.get("title"), "Unknown Title"),
                    "location": _clean(row.get("location"), "Unknown"),
                    "source_url": source_url,
                    "description": _clean(row.get("description"), ""),
                    "date_posted": _clean(row.get("date_posted"), ""),
                    "job_board": _clean(row.get("job_board"), default_job_board).lower(),
                    "user_id": _clean(row.get("user_id"), ""),
                }
            )
    return jobs
