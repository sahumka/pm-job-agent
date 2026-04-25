from __future__ import annotations

import argparse
import csv
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from src.db import init_db, insert_job
from src.email_digest import generate_and_send_digest
from src.logging_utils import configure_logging
from src.runtime_config import env_bool, env_int
from src.score_job import compact_text, score_job
from src.scrapers import scrape_company_jobs
from src.scrapers.linkedin import load_linkedin_jobs_from_csv
from src.scrapers.manual_imports import load_jobs_from_csv
from src.user_context import get_active_user, load_profile

configure_logging("run_daily")
LOGGER = logging.getLogger(__name__)
HIGH_QUALITY_THRESHOLD = 4.0


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_company_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {str(k).strip(): str(v or "").strip() for k, v in row.items()}
            if normalized.get("company_name", "").startswith("#"):
                continue
            if not normalized.get("company_name") or not normalized.get("careers_url"):
                continue
            if normalized.get("enabled", "true").lower() in {"false", "0", "no"}:
                continue
            rows.append(normalized)
        return rows


def title_matches_profile(title: str, context: dict[str, Any], extra_role_keywords: list[str] | None = None) -> bool:
    """Fast role filter before scoring to reduce noise."""
    title_l = title.lower()
    target_roles = [str(x).lower().strip() for x in context.get("target_roles", []) if str(x).strip()]
    if any(role in title_l for role in target_roles):
        return True

    tokens: set[str] = set()
    for role in target_roles:
        for token in role.replace("/", " ").split():
            token = token.strip().lower()
            if len(token) >= 4 and token not in {"senior", "manager"}:
                tokens.add(token)

    for keyword in extra_role_keywords or []:
        for token in keyword.lower().split():
            if len(token) >= 4:
                tokens.add(token)

    return any(token in title_l for token in tokens)


def _resolve_row_users(row: dict[str, str], cli_user_id: str | None) -> list[str]:
    if cli_user_id:
        return [cli_user_id]
    row_user = row.get("user_id", "").strip()
    if row_user:
        return _split_csv(row_user)
    active = get_active_user()
    return [active] if active else ["default"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run daily scraping and scoring pipeline")
    parser.add_argument("--companies-csv", default="config/target_companies.csv", help="Target companies CSV file path")
    parser.add_argument("--linkedin-csv", default="config/linkedin_jobs.csv", help="LinkedIn jobs CSV import path")
    parser.add_argument(
        "--manual-jobs-csv",
        default="config/manual_jobs.csv",
        help="Generic manual jobs CSV import path (supports linkedin/wellfound/builtin/etc.)",
    )
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--user-id", default=None, help="Optional single user profile to run for")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--output-digest", default="outputs/daily_digest.html", help="Digest HTML output path")
    parser.add_argument("--skip-digest", action="store_true", help="Skip digest generation/email step")
    return parser


def _insert_scored_job(
    company_name: str,
    job: dict[str, str],
    context: dict[str, Any],
    db_path: str,
    summary: dict[str, Any],
) -> None:
    title = str(job.get("title", ""))
    score = score_job(
        {
            "title": title,
            "description": str(job.get("description", "")),
            "location": str(job.get("location", "Unknown")),
            "source_url": str(job.get("source_url", "")),
        },
        context=context,
    )

    payload = {
        "user_id": context["user_id"],
        "company": str(job.get("company", company_name)),
        "title": title,
        "location": str(job.get("location", "Unknown")),
        "source_url": str(job.get("source_url", "")),
        "job_board": str(job.get("job_board", "generic")),
        "description": compact_text(str(job.get("description", ""))),
        "date_found": date.today().isoformat(),
        "date_posted": str(job.get("date_posted", "")) or None,
        "status": "New",
        "fit_score": score["fit_score"],
        "score_reason": score["score_reason"],
        "gaps": json.dumps(score["gaps"]),
        "resume_keywords": json.dumps(score["resume_keywords"]),
        "notes": f"Recommendation: {score['recommendation']}",
    }

    try:
        inserted = insert_job(payload, db_path=db_path)
    except Exception:
        summary["errors"] += 1
        LOGGER.exception("Failed to save job: %s | %s", company_name, title)
        return

    if inserted:
        summary["jobs_inserted"] += 1
        if float(score.get("fit_score", 0) or 0) >= HIGH_QUALITY_THRESHOLD:
            summary["high_quality_inserted"] += 1
    else:
        summary["duplicates_skipped"] += 1


def run_daily(
    companies_csv: str,
    linkedin_csv: str,
    manual_jobs_csv: str,
    db_path: str,
    user_id: str | None = None,
    timeout: int = 20,
    output_digest: str = "outputs/daily_digest.html",
    skip_digest: bool = False,
) -> dict[str, Any]:
    init_db(db_path)
    rows = _load_company_rows(Path(companies_csv))
    profile_cache: dict[str, dict[str, Any]] = {}
    source_health: list[dict[str, Any]] = []

    summary = {
        "companies_processed": 0,
        "jobs_scraped": 0,
        "jobs_matched_role_filter": 0,
        "jobs_inserted": 0,
        "high_quality_inserted": 0,
        "duplicates_skipped": 0,
        "linkedin_rows_loaded": 0,
        "linkedin_rows_matched": 0,
        "manual_rows_loaded": 0,
        "manual_rows_matched": 0,
        "errors": 0,
        "digest_generated": False,
        "digest_path": "",
        "email_sent": False,
        "email_error": "",
        "email_skipped_missing_config": False,
    }

    for row in rows:
        company_name = row["company_name"]
        careers_url = row["careers_url"]
        job_board = row.get("job_board", "")
        extra_role_keywords = _split_csv(row.get("role_keywords", ""))

        scraped = scrape_company_jobs(
            company_name=company_name,
            careers_url=careers_url,
            job_board=job_board,
            timeout=timeout,
        )
        company_inserted_before = summary["jobs_inserted"]
        company_dupes_before = summary["duplicates_skipped"]
        summary["companies_processed"] += 1
        summary["jobs_scraped"] += len(scraped)

        for uid in _resolve_row_users(row, cli_user_id=user_id):
            if uid not in profile_cache:
                profile_cache[uid] = load_profile(user_id=uid)
            context = profile_cache[uid]

            for job in scraped:
                title = str(job.get("title", ""))
                if not title_matches_profile(title, context, extra_role_keywords=extra_role_keywords):
                    continue

                summary["jobs_matched_role_filter"] += 1
                _insert_scored_job(company_name=company_name, job=job, context=context, db_path=db_path, summary=summary)

        company_inserted = int(summary["jobs_inserted"] - company_inserted_before)
        company_dupes = int(summary["duplicates_skipped"] - company_dupes_before)
        scraped_n = int(len(scraped))
        match_rate = (company_inserted / scraped_n) if scraped_n > 0 else 0.0
        score = int(round(100 * match_rate)) if scraped_n > 0 else 0
        source_health.append(
            {
                "company_name": company_name,
                "careers_url": careers_url,
                "job_board": job_board or "auto",
                "jobs_scraped": scraped_n,
                "jobs_inserted": company_inserted,
                "duplicates_skipped": company_dupes,
                "health_score": score,
                "health_label": "good" if score >= 40 else ("fair" if score >= 15 else "poor"),
            }
        )

    linkedin_jobs = load_linkedin_jobs_from_csv(linkedin_csv)
    summary["linkedin_rows_loaded"] = len(linkedin_jobs)
    linkedin_user_ids = [user_id] if user_id else ([get_active_user()] if get_active_user() else ["default"])

    for uid in linkedin_user_ids:
        uid = uid or "default"
        if uid not in profile_cache:
            profile_cache[uid] = load_profile(user_id=uid)
        context = profile_cache[uid]

        for job in linkedin_jobs:
            title = str(job.get("title", ""))
            if not title_matches_profile(title, context, extra_role_keywords=[]):
                continue
            summary["linkedin_rows_matched"] += 1
            summary["jobs_matched_role_filter"] += 1
            _insert_scored_job(company_name=str(job.get("company", "LinkedIn Import")), job=job, context=context, db_path=db_path, summary=summary)

    manual_jobs = load_jobs_from_csv(manual_jobs_csv, default_job_board="manual")
    summary["manual_rows_loaded"] = len(manual_jobs)
    default_user_ids = [user_id] if user_id else ([get_active_user()] if get_active_user() else ["default"])

    for job in manual_jobs:
        row_user = str(job.get("user_id", "")).strip()
        row_user_ids = [row_user] if row_user else default_user_ids
        for uid in row_user_ids:
            uid = uid or "default"
            if uid not in profile_cache:
                profile_cache[uid] = load_profile(user_id=uid)
            context = profile_cache[uid]

            title = str(job.get("title", ""))
            if not title_matches_profile(title, context, extra_role_keywords=[]):
                continue
            summary["manual_rows_matched"] += 1
            summary["jobs_matched_role_filter"] += 1
            _insert_scored_job(company_name=str(job.get("company", "Manual Import")), job=job, context=context, db_path=db_path, summary=summary)

    if not skip_digest:
        digest_result = generate_and_send_digest(
            db_path=db_path,
            output_path=output_digest,
            user_id=user_id,
            top_n=10,
        )
        summary["digest_generated"] = True
        summary["digest_path"] = digest_result["digest_path"]
        summary["email_sent"] = bool(digest_result["email_sent"])
        summary["email_error"] = str(digest_result["email_error"])
        summary["email_skipped_missing_config"] = bool(digest_result["email_skipped_missing_config"])

    # Persist source health diagnostics for quick inspection/tuning.
    health_dir = Path("outputs")
    health_dir.mkdir(parents=True, exist_ok=True)
    source_health_sorted = sorted(source_health, key=lambda x: (x["health_score"], x["jobs_scraped"]))
    (health_dir / "source_health.json").write_text(json.dumps(source_health_sorted, indent=2), encoding="utf-8")
    with (health_dir / "source_health.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "company_name",
                "careers_url",
                "job_board",
                "jobs_scraped",
                "jobs_inserted",
                "duplicates_skipped",
                "health_score",
                "health_label",
            ],
        )
        writer.writeheader()
        writer.writerows(source_health_sorted)

    # Optional guardrail: auto-disable poor sources that scrape zero roles.
    if env_bool("SOURCE_AUTO_DISABLE_EMPTY", default=False):
        threshold = max(0, env_int("SOURCE_AUTO_DISABLE_SCORE_MAX", 5))
        _auto_disable_poor_sources(Path(companies_csv), source_health_sorted, threshold=threshold)

    LOGGER.info("Daily run summary: %s", summary)
    return summary


def _auto_disable_poor_sources(csv_path: Path, source_health: list[dict[str, Any]], threshold: int) -> None:
    if not csv_path.exists():
        return
    by_company = {str(x.get("company_name", "")).strip().lower(): x for x in source_health}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows:
        return

    changed = 0
    for row in rows:
        key = str(row.get("company_name", "")).strip().lower()
        health = by_company.get(key)
        if not health:
            continue
        if int(health.get("jobs_scraped", 0)) == 0 and int(health.get("health_score", 0)) <= threshold:
            if str(row.get("enabled", "true")).strip().lower() not in {"false", "0", "no"}:
                row["enabled"] = "false"
                changed += 1

    if changed:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        LOGGER.warning("Auto-disabled %s low-health sources in %s", changed, csv_path)


def main() -> None:
    args = build_parser().parse_args()
    summary = run_daily(
        companies_csv=args.companies_csv,
        linkedin_csv=args.linkedin_csv,
        manual_jobs_csv=args.manual_jobs_csv,
        db_path=args.db_path,
        user_id=args.user_id,
        timeout=args.timeout,
        output_digest=args.output_digest,
        skip_digest=args.skip_digest,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
