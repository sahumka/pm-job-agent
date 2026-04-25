from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.db import init_db


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"]) if row else 0


def _load_profile_ids(root: Path = Path("config/users")) -> list[str]:
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.yaml"))


def build_health_report(db_path: Path) -> dict[str, Any]:
    db_path = Path(db_path)
    init_db(db_path)

    report: dict[str, Any] = {
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "profiles": _load_profile_ids(),
        "outputs_exists": Path("outputs").exists(),
        "config_exists": Path("config").exists(),
        "data_exists": Path("data").exists(),
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        report["jobs_total"] = _count_rows(conn, "jobs")
        report["runs_total"] = _count_rows(conn, "fetch_runs")
        report["recent_runs"] = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, run_type, profile_id, status, started_at, finished_at,
                       companies_processed, jobs_inserted, duplicates_skipped, errors
                FROM fetch_runs
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run quick PM Copilot system health checks.")
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite database path.")
    parser.add_argument(
        "--output-json",
        default="outputs/healthcheck.json",
        help="Path to write JSON report.",
    )
    args = parser.parse_args()

    report = build_health_report(Path(args.db_path))
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Healthcheck complete")
    print(f"DB: {report['db_path']} (exists={report['db_exists']})")
    print(f"Profiles: {', '.join(report['profiles']) if report['profiles'] else 'none found'}")
    print(f"Jobs: {report['jobs_total']} | Runs: {report['runs_total']}")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
