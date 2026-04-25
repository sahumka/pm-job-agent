from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.dedupe import dedupe_key

LOGGER = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path("data/jobs.db")


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a sqlite connection with dictionary-like rows."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create tables and indexes for the PM Job Search Copilot."""
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                source_url TEXT NOT NULL,
                job_board TEXT,
                description TEXT,
                date_found TEXT NOT NULL,
                date_posted TEXT,
                status TEXT NOT NULL DEFAULT 'New',
                fit_score REAL,
                score_reason TEXT,
                gaps TEXT,
                resume_keywords TEXT,
                applied_date TEXT,
                follow_up_date TEXT,
                notes TEXT,
                dedupe_key TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_user_source_url
            ON jobs(user_id, source_url);

            CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_user_dedupe_key
            ON jobs(user_id, dedupe_key);

            CREATE INDEX IF NOT EXISTS ix_jobs_date_found
            ON jobs(date_found);

            CREATE INDEX IF NOT EXISTS ix_jobs_status
            ON jobs(status);

            CREATE INDEX IF NOT EXISTS ix_jobs_user_id
            ON jobs(user_id);

            CREATE TABLE IF NOT EXISTS fetch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL DEFAULT 'hourly',
                profile_id TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT,
                companies_processed INTEGER NOT NULL DEFAULT 0,
                jobs_scraped INTEGER NOT NULL DEFAULT 0,
                jobs_matched_role_filter INTEGER NOT NULL DEFAULT 0,
                jobs_inserted INTEGER NOT NULL DEFAULT 0,
                duplicates_skipped INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS ix_fetch_runs_started_at
            ON fetch_runs(started_at);

            CREATE INDEX IF NOT EXISTS ix_fetch_runs_profile_id
            ON fetch_runs(profile_id);
            """
        )
        _run_migrations(conn)
        conn.commit()
        LOGGER.info("Database initialized at %s", Path(db_path).resolve())
    finally:
        conn.close()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        (index_name,),
    ).fetchall()
    return bool(rows)


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Apply additive migrations for local development databases."""
    if not _column_exists(conn, "jobs", "user_id"):
        conn.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT DEFAULT 'default'")
        conn.execute("UPDATE jobs SET user_id = 'default' WHERE user_id IS NULL OR user_id = ''")
    if not _column_exists(conn, "jobs", "follow_up_date"):
        conn.execute("ALTER TABLE jobs ADD COLUMN follow_up_date TEXT")

    # Replace global dedupe with per-user dedupe so multiple people can track same job.
    if _index_exists(conn, "ux_jobs_source_url"):
        conn.execute("DROP INDEX ux_jobs_source_url")
    if _index_exists(conn, "ux_jobs_dedupe_key"):
        conn.execute("DROP INDEX ux_jobs_dedupe_key")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_user_source_url
        ON jobs(user_id, source_url)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_user_dedupe_key
        ON jobs(user_id, dedupe_key)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_jobs_user_id
        ON jobs(user_id)
        """
    )


def insert_job(job: dict[str, Any], db_path: Path | str = DEFAULT_DB_PATH) -> bool:
    """
    Insert a job if not duplicate.

    Returns True if inserted, False if duplicate.
    """
    required_fields = ["company", "title", "location", "source_url", "date_found"]
    missing = [field for field in required_fields if not job.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    payload = dict(job)
    payload["user_id"] = str(payload.get("user_id", "default")).strip() or "default"
    payload["dedupe_key"] = dedupe_key(
        payload["company"], payload["title"], payload["location"]
    )

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO jobs (
                user_id, company, title, location, source_url, job_board, description,
                date_found, date_posted, status, fit_score, score_reason, gaps,
                resume_keywords, applied_date, follow_up_date, notes, dedupe_key
            ) VALUES (
                :user_id, :company, :title, :location, :source_url, :job_board, :description,
                :date_found, :date_posted, :status, :fit_score, :score_reason, :gaps,
                :resume_keywords, :applied_date, :follow_up_date, :notes, :dedupe_key
            )
            """,
            {
                "user_id": payload["user_id"],
                "company": payload["company"],
                "title": payload["title"],
                "location": payload["location"],
                "source_url": payload["source_url"],
                "job_board": payload.get("job_board", "unknown"),
                "description": payload.get("description", ""),
                "date_found": payload["date_found"],
                "date_posted": payload.get("date_posted"),
                "status": payload.get("status", "New"),
                "fit_score": payload.get("fit_score"),
                "score_reason": payload.get("score_reason"),
                "gaps": payload.get("gaps"),
                "resume_keywords": payload.get("resume_keywords"),
                "applied_date": payload.get("applied_date"),
                "follow_up_date": payload.get("follow_up_date"),
                "notes": payload.get("notes"),
                "dedupe_key": payload["dedupe_key"],
            },
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        LOGGER.info(
            "Duplicate skipped for user_id=%s source_url=%s or key=%s",
            payload.get("user_id"),
            payload.get("source_url"),
            payload.get("dedupe_key"),
        )
        return False
    finally:
        conn.close()


def list_user_ids(db_path: Path | str = DEFAULT_DB_PATH) -> list[str]:
    """Return known user ids from the jobs table."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM jobs WHERE user_id IS NOT NULL AND user_id != '' ORDER BY user_id"
        ).fetchall()
        return [str(row["user_id"]) for row in rows]
    finally:
        conn.close()


def query_jobs(
    db_path: Path | str = DEFAULT_DB_PATH,
    user_id: str | None = None,
    company: str | None = None,
    location: str | None = None,
    min_score: float | None = None,
    status: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Query jobs with optional filters."""
    conn = get_connection(db_path)
    try:
        sql = [
            """
            SELECT
                id, user_id, company, title, location, source_url, job_board,
                description, date_found, date_posted, status, fit_score, score_reason,
                gaps, resume_keywords, applied_date, follow_up_date, notes, created_at, updated_at
            FROM jobs
            WHERE 1=1
            """
        ]
        params: list[Any] = []

        if user_id:
            sql.append("AND user_id = ?")
            params.append(user_id)
        if company:
            sql.append("AND lower(company) LIKE ?")
            params.append(f"%{company.strip().lower()}%")
        if location:
            sql.append("AND lower(location) LIKE ?")
            params.append(f"%{location.strip().lower()}%")
        if min_score is not None:
            sql.append("AND COALESCE(fit_score, 0) >= ?")
            params.append(float(min_score))
        if status:
            sql.append("AND status = ?")
            params.append(status)

        sql.append("ORDER BY COALESCE(fit_score, 0) DESC, created_at DESC")
        sql.append("LIMIT ?")
        params.append(int(limit))

        rows = conn.execute(" ".join(sql), params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_job(
    job_id: int,
    db_path: Path | str = DEFAULT_DB_PATH,
    status: str | None = None,
    notes: str | None = None,
    applied_date: str | None = None,
    follow_up_date: str | None = None,
) -> bool:
    """Update mutable job fields from the tracker UI."""
    assignments: list[str] = []
    params: list[Any] = []

    if status is not None:
        assignments.append("status = ?")
        params.append(status)
    if notes is not None:
        assignments.append("notes = ?")
        params.append(notes)
    if applied_date is not None:
        assignments.append("applied_date = ?")
        params.append(applied_date)
    if follow_up_date is not None:
        assignments.append("follow_up_date = ?")
        params.append(follow_up_date)

    if not assignments:
        return False

    assignments.append("updated_at = datetime('now')")
    params.append(int(job_id))

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?",
            params,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_jobs(
    job_ids: list[int],
    db_path: Path | str = DEFAULT_DB_PATH,
    user_id: str | None = None,
) -> int:
    """Delete jobs by id. Returns number of rows deleted."""
    clean_ids = sorted({int(x) for x in job_ids if str(x).strip()})
    if not clean_ids:
        return 0

    placeholders = ",".join("?" for _ in clean_ids)
    sql = [f"DELETE FROM jobs WHERE id IN ({placeholders})"]
    params: list[Any] = list(clean_ids)

    if user_id:
        sql.append("AND user_id = ?")
        params.append(str(user_id))

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(" ".join(sql), params)
        conn.commit()
        return int(cursor.rowcount)
    finally:
        conn.close()


def start_fetch_run(
    db_path: Path | str = DEFAULT_DB_PATH,
    run_type: str = "hourly",
    profile_id: str | None = None,
) -> int:
    """Create a fetch run record and return the run id."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO fetch_runs (run_type, profile_id, status)
            VALUES (?, ?, 'running')
            """,
            (run_type, profile_id),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def finish_fetch_run(
    run_id: int,
    db_path: Path | str = DEFAULT_DB_PATH,
    status: str = "success",
    companies_processed: int = 0,
    jobs_scraped: int = 0,
    jobs_matched_role_filter: int = 0,
    jobs_inserted: int = 0,
    duplicates_skipped: int = 0,
    errors: int = 0,
    notes: str = "",
) -> bool:
    """Finalize a fetch run with metrics."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            UPDATE fetch_runs
            SET
                status = ?,
                finished_at = datetime('now'),
                companies_processed = ?,
                jobs_scraped = ?,
                jobs_matched_role_filter = ?,
                jobs_inserted = ?,
                duplicates_skipped = ?,
                errors = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                status,
                int(companies_processed),
                int(jobs_scraped),
                int(jobs_matched_role_filter),
                int(jobs_inserted),
                int(duplicates_skipped),
                int(errors),
                notes,
                int(run_id),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def query_fetch_runs(
    db_path: Path | str = DEFAULT_DB_PATH,
    profile_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent fetch runs, newest first."""
    conn = get_connection(db_path)
    try:
        sql = [
            """
            SELECT
                id, run_type, profile_id, status, started_at, finished_at,
                companies_processed, jobs_scraped, jobs_matched_role_filter,
                jobs_inserted, duplicates_skipped, errors, notes
            FROM fetch_runs
            WHERE 1=1
            """
        ]
        params: list[Any] = []
        if profile_id:
            sql.append("AND profile_id = ?")
            params.append(profile_id)
        sql.append("ORDER BY id DESC")
        sql.append("LIMIT ?")
        params.append(int(limit))

        rows = conn.execute(" ".join(sql), params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
