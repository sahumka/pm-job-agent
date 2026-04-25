from __future__ import annotations

import argparse
import json

from src.run_daily import run_daily


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import manual jobs CSV into SQLite with scoring")
    parser.add_argument("--manual-jobs-csv", default="config/manual_jobs.csv", help="Manual jobs CSV import path")
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--user-id", default=None, help="Optional profile for rows without user_id")
    parser.add_argument("--companies-csv", default="", help="Optional companies CSV path")
    parser.add_argument("--linkedin-csv", default="", help="Optional LinkedIn CSV path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_daily(
        companies_csv=args.companies_csv,
        linkedin_csv=args.linkedin_csv,
        manual_jobs_csv=args.manual_jobs_csv,
        db_path=args.db_path,
        user_id=args.user_id,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
