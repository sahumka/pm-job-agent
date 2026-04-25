from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from src.dashboard_utils import follow_up_queue
from src.db import (
    delete_jobs,
    finish_fetch_run,
    init_db,
    list_user_ids,
    query_fetch_runs,
    query_jobs,
    start_fetch_run,
    update_job,
)
from src.user_context import get_active_user, load_profile, save_profile, set_active_user


def ensure_db(db_path: str) -> None:
    init_db(db_path)


def get_profiles() -> list[str]:
    root = Path("config/users")
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.yaml"))


def get_active_profile() -> str | None:
    return get_active_user()


def set_active_profile(user_id: str) -> None:
    set_active_user(user_id)


def load_profile_data(user_id: str | None) -> dict[str, Any]:
    return load_profile(user_id=user_id)


def save_profile_data(profile: dict[str, Any], set_active: bool = False) -> str:
    path = save_profile(profile)
    if set_active and profile.get("user_id"):
        set_active_user(str(profile["user_id"]))
    return str(path)


def get_jobs(
    db_path: str,
    user_id: str | None = None,
    company: str | None = None,
    location: str | None = None,
    min_score: float | None = None,
    status: str | None = None,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    return query_jobs(
        db_path=db_path,
        user_id=user_id,
        company=company,
        location=location,
        min_score=min_score,
        status=status,
        limit=limit,
    )


def list_users(db_path: str) -> list[str]:
    return list_user_ids(db_path=db_path)


def save_job_update(
    db_path: str,
    job_id: int,
    status: str | None = None,
    notes: str | None = None,
    applied_date: str | None = None,
    follow_up_date: str | None = None,
) -> bool:
    return update_job(
        job_id=job_id,
        db_path=db_path,
        status=status,
        notes=notes,
        applied_date=applied_date,
        follow_up_date=follow_up_date,
    )


def delete_jobs_by_ids(db_path: str, job_ids: list[int], user_id: str | None = None) -> int:
    return delete_jobs(job_ids=job_ids, db_path=db_path, user_id=user_id)


def create_fetch_run(db_path: str, run_type: str = "hourly", profile_id: str | None = None) -> int:
    return start_fetch_run(db_path=db_path, run_type=run_type, profile_id=profile_id)


def complete_fetch_run(
    db_path: str,
    run_id: int,
    status: str,
    companies_processed: int = 0,
    jobs_scraped: int = 0,
    jobs_matched_role_filter: int = 0,
    jobs_inserted: int = 0,
    duplicates_skipped: int = 0,
    errors: int = 0,
    notes: str = "",
) -> bool:
    return finish_fetch_run(
        run_id=run_id,
        db_path=db_path,
        status=status,
        companies_processed=companies_processed,
        jobs_scraped=jobs_scraped,
        jobs_matched_role_filter=jobs_matched_role_filter,
        jobs_inserted=jobs_inserted,
        duplicates_skipped=duplicates_skipped,
        errors=errors,
        notes=notes,
    )


def get_fetch_runs(db_path: str, profile_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return query_fetch_runs(db_path=db_path, profile_id=profile_id, limit=limit)


def dashboard_snapshot(rows: list[dict[str, Any]]) -> dict[str, int]:
    statuses = [str(r.get("status", "New")) for r in rows]
    today = date.today().isoformat()

    high_fit = sum(1 for r in rows if float(r.get("fit_score", 0) or 0) >= 4.0)
    apps_started = sum(1 for s in statuses if s in {"Applied", "Recruiter Screen", "Interview", "Offer"})
    interviews = sum(1 for s in statuses if s in {"Interview", "Offer"})
    follow_ups = len(follow_up_queue(rows))

    return {
        "jobs_ingested": len(rows),
        "jobs_scored": sum(1 for r in rows if r.get("fit_score") is not None),
        "high_fit_roles": high_fit,
        "applications_started": apps_started,
        "interviews": interviews,
        "follow_ups_due": follow_ups,
        "new_today": sum(1 for r in rows if str(r.get("date_found", "")) == today),
    }


def top_matching_roles(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda x: float(x.get("fit_score", 0) or 0), reverse=True)[:limit]
