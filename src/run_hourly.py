from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.db import finish_fetch_run, init_db, start_fetch_run
from src.logging_utils import configure_logging
from src.profile_sources import resolve_sources_for_profile
from src.run_daily import run_daily
from src.user_context import get_profile_status, list_crawl_enabled_profiles

configure_logging("run_hourly")
LOGGER = logging.getLogger(__name__)


def list_profile_ids(root: Path = Path("config/users")) -> list[str]:
    return list_crawl_enabled_profiles(root=root)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hourly scrape/score pipeline for one or more profiles.")
    parser.add_argument("--companies-csv", default="config/target_companies.csv", help="Target companies CSV file path")
    parser.add_argument("--linkedin-csv", default="config/linkedin_jobs.csv", help="LinkedIn jobs CSV import path")
    parser.add_argument(
        "--manual-jobs-csv",
        default="config/manual_jobs.csv",
        help="Manual jobs CSV import path",
    )
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--profiles", default="", help="Optional comma-separated profile ids to run")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument(
        "--use-profile-sources",
        default="true",
        help="Use per-profile CSV files under config/users/<profile>/ (true/false).",
    )
    parser.add_argument(
        "--summary-path",
        default="outputs/hourly_summary.json",
        help="Where to write the hourly JSON summary",
    )
    return parser


def run_hourly(
    companies_csv: str,
    linkedin_csv: str,
    manual_jobs_csv: str,
    db_path: str,
    profiles: list[str] | None = None,
    timeout: int = 20,
    use_profile_sources: bool = True,
    summary_path: str = "outputs/hourly_summary.json",
) -> dict[str, Any]:
    init_db(db_path)
    requested_profiles = profiles or list_profile_ids()
    target_profiles: list[str] = []
    skipped_profiles: list[dict[str, Any]] = []
    for pid in requested_profiles:
        status = get_profile_status(pid)
        if bool(status.get("configured")) and bool(status.get("crawl_active")):
            target_profiles.append(str(status.get("user_id", pid)))
        else:
            skipped_profiles.append(
                {
                    "profile_id": str(status.get("user_id", pid)),
                    "configured": bool(status.get("configured")),
                    "crawl_active": bool(status.get("crawl_active")),
                    "reason": "inactive_or_not_configured",
                }
            )

    if not target_profiles:
        LOGGER.warning("No runnable profiles found for hourly crawl.")

    output: dict[str, Any] = {
        "run_type": "hourly",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "profiles_requested": requested_profiles,
        "profiles_skipped": skipped_profiles,
        "profiles_ran": target_profiles,
        "profile_runs": [],
        "totals": {
            "companies_processed": 0,
            "jobs_scraped": 0,
            "jobs_matched_role_filter": 0,
            "jobs_inserted": 0,
            "high_quality_inserted": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "profiles_succeeded": 0,
            "profiles_failed": 0,
        },
    }

    for profile_id in target_profiles:
        run_id = start_fetch_run(db_path=db_path, run_type="hourly", profile_id=profile_id)
        LOGGER.info("Starting hourly profile run | profile=%s | run_id=%s", profile_id, run_id)
        source_paths = resolve_sources_for_profile(
            profile_id=profile_id,
            companies_csv=companies_csv,
            linkedin_csv=linkedin_csv,
            manual_jobs_csv=manual_jobs_csv,
            use_profile_sources=use_profile_sources,
        )

        try:
            summary = run_daily(
                companies_csv=source_paths["companies_csv"],
                linkedin_csv=source_paths["linkedin_csv"],
                manual_jobs_csv=source_paths["manual_jobs_csv"],
                db_path=db_path,
                user_id=profile_id,
                timeout=timeout,
                skip_digest=True,  # hourly runs should not send frequent email digests
            )
            finish_fetch_run(
                run_id=run_id,
                db_path=db_path,
                status="success",
                companies_processed=int(summary.get("companies_processed", 0)),
                jobs_scraped=int(summary.get("jobs_scraped", 0)),
                jobs_matched_role_filter=int(summary.get("jobs_matched_role_filter", 0)),
                jobs_inserted=int(summary.get("jobs_inserted", 0)),
                duplicates_skipped=int(summary.get("duplicates_skipped", 0)),
                errors=int(summary.get("errors", 0)),
                notes="hourly run completed",
            )

            output["profile_runs"].append(
                {
                    "profile_id": profile_id,
                    "fetch_run_id": run_id,
                    "status": "success",
                    "sources": source_paths,
                    "summary": summary,
                }
            )
            output["totals"]["profiles_succeeded"] += 1
            for key in (
                "companies_processed",
                "jobs_scraped",
                "jobs_matched_role_filter",
                "jobs_inserted",
                "high_quality_inserted",
                "duplicates_skipped",
                "errors",
            ):
                output["totals"][key] += int(summary.get(key, 0))
        except Exception as exc:
            LOGGER.exception("Hourly run failed | profile=%s | run_id=%s", profile_id, run_id)
            output["profile_runs"].append(
                {
                    "profile_id": profile_id,
                    "fetch_run_id": run_id,
                    "status": "failed",
                    "sources": source_paths,
                    "error": str(exc),
                }
            )
            output["totals"]["profiles_failed"] += 1
            output["totals"]["errors"] += 1
            finish_fetch_run(
                run_id=run_id,
                db_path=db_path,
                status="failed",
                errors=1,
                notes=str(exc)[:4000],
            )

    output["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary_target = Path(summary_path)
    summary_target.parent.mkdir(parents=True, exist_ok=True)
    summary_target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    LOGGER.info("Hourly run complete. Summary written to %s", summary_target)
    return output


def main() -> None:
    args = build_parser().parse_args()
    selected_profiles = _split_csv(args.profiles) if args.profiles else []
    summary = run_hourly(
        companies_csv=args.companies_csv,
        linkedin_csv=args.linkedin_csv,
        manual_jobs_csv=args.manual_jobs_csv,
        db_path=args.db_path,
        profiles=selected_profiles,
        timeout=args.timeout,
        use_profile_sources=_parse_bool(args.use_profile_sources),
        summary_path=args.summary_path,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
