from __future__ import annotations

import argparse
import json

from src.run_daily import run_daily


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import LinkedIn CSV jobs into SQLite with scoring")
    parser.add_argument("--linkedin-csv", default="config/linkedin_jobs.csv", help="LinkedIn CSV import path")
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--user-id", default=None, help="Optional single profile for scoring/import")
    parser.add_argument("--companies-csv", default="", help="Optional companies CSV (leave empty for LinkedIn-only)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_daily(
        companies_csv=args.companies_csv,
        linkedin_csv=args.linkedin_csv,
        manual_jobs_csv="",
        db_path=args.db_path,
        user_id=args.user_id,
        skip_digest=False,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
