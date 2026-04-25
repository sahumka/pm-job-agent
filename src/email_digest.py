from __future__ import annotations

import argparse
import html
import json
import logging
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback when dependency missing
    def load_dotenv() -> bool:  # type: ignore[misc]
        return False

from src.db import get_connection
from src.logging_utils import configure_logging

try:
    from src.user_context import get_active_user
except Exception:  # pragma: no cover - fallback when YAML dependency is missing
    def get_active_user() -> str | None:  # type: ignore[misc]
        return None

LOGGER = logging.getLogger(__name__)
configure_logging("email_digest")


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


def fetch_jobs_for_digest(
    db_path: str = "data/jobs.db",
    user_id: str | None = None,
    limit: int = 10,
    for_date: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Return (top_jobs, total_new_jobs) for the given date and optional user.
    """
    target_date = for_date or date.today().isoformat()
    resolved_user_id = user_id if user_id else get_active_user()

    conn = get_connection(db_path)
    try:
        if resolved_user_id:
            total = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE date_found = ? AND user_id = ?",
                (target_date, resolved_user_id),
            ).fetchone()[0]

            rows = conn.execute(
                """
                SELECT id, user_id, company, title, location, source_url, fit_score, score_reason, gaps, notes, date_found
                FROM jobs
                WHERE date_found = ? AND user_id = ?
                ORDER BY COALESCE(fit_score, 0) DESC, created_at DESC
                LIMIT ?
                """,
                (target_date, resolved_user_id, limit),
            ).fetchall()
        else:
            total = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE date_found = ?",
                (target_date,),
            ).fetchone()[0]

            rows = conn.execute(
                """
                SELECT id, user_id, company, title, location, source_url, fit_score, score_reason, gaps, notes, date_found
                FROM jobs
                WHERE date_found = ?
                ORDER BY COALESCE(fit_score, 0) DESC, created_at DESC
                LIMIT ?
                """,
                (target_date, limit),
            ).fetchall()
    finally:
        conn.close()

    jobs: list[dict[str, Any]] = []
    for row in rows:
        jobs.append(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "company": row["company"],
                "title": row["title"],
                "location": row["location"],
                "source_url": row["source_url"],
                "fit_score": row["fit_score"],
                "score_reason": row["score_reason"] or "",
                "gaps": _parse_json_list(row["gaps"]),
                "notes": row["notes"] or "",
                "date_found": row["date_found"],
            }
        )
    return jobs, int(total)


def render_digest_html(
    jobs: list[dict[str, Any]],
    total_new_jobs: int,
    user_id: str | None = None,
    target_date: str | None = None,
) -> str:
    digest_date = target_date or date.today().isoformat()
    scope_text = f" for user '{html.escape(user_id)}'" if user_id else ""

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append("<html><head><meta charset='utf-8'><title>PM Job Search Copilot Digest</title>")
    parts.append(
        "<style>"
        "body{font-family:Arial,sans-serif;background:#f7f7fb;color:#222;margin:0;padding:20px;}"
        ".card{background:#fff;border:1px solid #e2e2ee;border-radius:10px;padding:14px 16px;margin:12px 0;}"
        ".muted{color:#666;font-size:13px;}"
        ".score{font-weight:bold;color:#0a6;}"
        "a{color:#0b5bd3;text-decoration:none;}"
        "h1,h2,h3{margin:0 0 8px 0;}"
        "ul{margin:8px 0 0 20px;}"
        "</style></head><body>"
    )
    parts.append(f"<h1>Daily Job Digest - {html.escape(digest_date)}</h1>")
    parts.append(f"<p class='muted'>Total new jobs{scope_text}: <strong>{total_new_jobs}</strong></p>")

    if not jobs:
        parts.append("<div class='card'><h3>No new jobs found today.</h3></div>")
        parts.append("</body></html>")
        return "".join(parts)

    parts.append("<h2>Top Jobs</h2>")
    for idx, job in enumerate(jobs, start=1):
        fit_score = job.get("fit_score")
        fit_text = f"{fit_score:.2f}/5" if isinstance(fit_score, (float, int)) else "N/A"
        reason = html.escape(str(job.get("score_reason", "")))
        gaps = [html.escape(str(g)) for g in job.get("gaps", [])[:4]]
        source_url = html.escape(str(job.get("source_url", "")))

        parts.append("<div class='card'>")
        parts.append(
            f"<h3>{idx}. {html.escape(str(job.get('title', '')))} at {html.escape(str(job.get('company', '')))}</h3>"
        )
        parts.append(
            f"<p><span class='score'>Fit Score: {fit_text}</span> | "
            f"Location: {html.escape(str(job.get('location', 'Unknown')))} | "
            f"User: {html.escape(str(job.get('user_id', 'default')))}</p>"
        )
        parts.append(f"<p><strong>Why it fits:</strong> {reason or 'No reason available.'}</p>")
        if gaps:
            parts.append("<p><strong>Gaps:</strong></p><ul>")
            for gap in gaps:
                parts.append(f"<li>{gap}</li>")
            parts.append("</ul>")
        parts.append(f"<p><a href='{source_url}'>Apply Link</a></p>")
        parts.append("</div>")

    parts.append("</body></html>")
    return "".join(parts)


def save_digest_html(html_content: str, output_path: str = "outputs/daily_digest.html") -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def send_digest_email(
    html_content: str,
    subject: str,
    email_from: str,
    email_password: str,
    email_to: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = email_to
    message.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.login(email_from, email_password)
        smtp.sendmail(email_from, [email_to], message.as_string())


def generate_and_send_digest(
    db_path: str = "data/jobs.db",
    output_path: str = "outputs/daily_digest.html",
    user_id: str | None = None,
    top_n: int = 10,
    for_date: str | None = None,
) -> dict[str, Any]:
    load_dotenv()

    jobs, total = fetch_jobs_for_digest(
        db_path=db_path,
        user_id=user_id,
        limit=top_n,
        for_date=for_date,
    )
    digest_date = for_date or date.today().isoformat()
    html_content = render_digest_html(jobs=jobs, total_new_jobs=total, user_id=user_id, target_date=digest_date)
    path = save_digest_html(html_content, output_path=output_path)

    email_from = os.getenv("EMAIL_FROM", "").strip()
    email_password = os.getenv("EMAIL_PASSWORD", "").strip()
    email_to = os.getenv("EMAIL_TO", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    email_sent = False
    email_error = ""
    if email_from and email_password and email_to:
        subject = f"PM Job Search Copilot Digest - {digest_date}"
        try:
            send_digest_email(
                html_content=html_content,
                subject=subject,
                email_from=email_from,
                email_password=email_password,
                email_to=email_to,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
            )
            email_sent = True
        except Exception as exc:
            email_error = str(exc)
            LOGGER.warning("Email send failed, digest still saved locally: %s", exc)
    else:
        LOGGER.info("Email settings missing, digest saved locally at %s", path)

    return {
        "digest_path": str(path),
        "total_new_jobs": total,
        "top_jobs_count": len(jobs),
        "email_sent": email_sent,
        "email_error": email_error,
        "email_skipped_missing_config": not (email_from and email_password and email_to),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and optionally email daily job digest")
    parser.add_argument("--db-path", default="data/jobs.db", help="SQLite DB path")
    parser.add_argument("--output-path", default="outputs/daily_digest.html", help="HTML output path")
    parser.add_argument("--user-id", default=None, help="Optional user id filter")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top jobs to include")
    parser.add_argument("--date", default=None, help="Date filter in YYYY-MM-DD (default: today)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = generate_and_send_digest(
        db_path=args.db_path,
        output_path=args.output_path,
        user_id=args.user_id,
        top_n=args.top_n,
        for_date=args.date,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
