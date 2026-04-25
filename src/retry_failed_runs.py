from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.db import get_connection, init_db
from src.run_hourly import run_hourly


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def latest_failed_profiles(
    db_path: str,
    run_types: list[str] | None = None,
    only_profiles: list[str] | None = None,
    limit: int = 5000,
) -> list[str]:
    """
    Match Streamlit Run History behavior:
    - failed = status != 'success'
    - pick latest failed row per profile_id (highest id)
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        sql = [
            """
            SELECT id, profile_id, status, run_type
            FROM fetch_runs
            WHERE profile_id IS NOT NULL
              AND TRIM(profile_id) != ''
              AND lower(COALESCE(status, '')) != 'success'
            """
        ]
        params: list[Any] = []

        if run_types:
            placeholders = ",".join("?" for _ in run_types)
            sql.append(f"AND run_type IN ({placeholders})")
            params.extend(run_types)

        if only_profiles:
            placeholders = ",".join("?" for _ in only_profiles)
            sql.append(f"AND profile_id IN ({placeholders})")
            params.extend(only_profiles)

        sql.append("ORDER BY id DESC")
        sql.append("LIMIT ?")
        params.append(int(limit))

        rows = [dict(r) for r in conn.execute(" ".join(sql), params).fetchall()]
    finally:
        conn.close()

    seen: set[str] = set()
    selected: list[str] = []
    for row in rows:
        profile_id = str(row.get("profile_id", "")).strip()
        if not profile_id or profile_id in seen:
            continue
        seen.add(profile_id)
        selected.append(profile_id)
    return sorted(selected)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retry latest failed fetch run per profile (GitHub Actions friendly)."
    )
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--companies-csv", default="config/target_companies.csv", help="Target companies CSV path")
    parser.add_argument("--linkedin-csv", default="config/linkedin_jobs.csv", help="LinkedIn CSV path")
    parser.add_argument("--manual-jobs-csv", default="config/manual_jobs.csv", help="Manual jobs CSV path")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout for retry run")
    parser.add_argument(
        "--run-types",
        default="hourly",
        help="Comma-separated run types to inspect for failures (default: hourly)",
    )
    parser.add_argument(
        "--profiles",
        default="",
        help="Optional comma-separated profiles to constrain retry selection",
    )
    parser.add_argument(
        "--selection-output",
        default="outputs/retry_latest_failed_profiles.json",
        help="Selection JSON path",
    )
    parser.add_argument(
        "--summary-path",
        default="outputs/hourly_retry_latest_summary.json",
        help="run_hourly summary JSON path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_types = _split_csv(args.run_types)
    profile_filter = _split_csv(args.profiles)

    selected = latest_failed_profiles(
        db_path=args.db_path,
        run_types=run_types or None,
        only_profiles=profile_filter or None,
        limit=10000,
    )

    selection_payload = {
        "mode": "latest_failed_per_profile",
        "run_types": run_types or ["hourly"],
        "profile_filter": profile_filter,
        "selected_profiles": selected,
        "selected_count": len(selected),
    }
    selection_path = Path(args.selection_output)
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    selection_path.write_text(json.dumps(selection_payload, indent=2), encoding="utf-8")

    if not selected:
        print(json.dumps({"message": "No failed profiles found for retry.", **selection_payload}, indent=2))
        return

    summary = run_hourly(
        companies_csv=args.companies_csv,
        linkedin_csv=args.linkedin_csv,
        manual_jobs_csv=args.manual_jobs_csv,
        db_path=args.db_path,
        profiles=selected,
        timeout=int(args.timeout),
        summary_path=args.summary_path,
    )
    result = {
        "selection": selection_payload,
        "summary_path": args.summary_path,
        "summary": summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
