from __future__ import annotations

import argparse
import json
import os
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from src.run_hourly import run_hourly
from src.user_context import load_profile


def _parse_profiles(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _send_email(subject: str, body: str, email_to: str | None = None) -> bool:
    email_from = os.getenv("EMAIL_FROM", "").strip()
    email_password = os.getenv("EMAIL_PASSWORD", "").strip()
    target_email = (email_to or os.getenv("EMAIL_TO", "")).strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not (email_from and email_password and target_email):
        return False

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = target_email

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.login(email_from, email_password)
        smtp.sendmail(email_from, [target_email], message.as_string())
    return True


def _format_totals(summary: dict[str, Any]) -> str:
    totals = summary.get("totals", {})
    lines = [
        f"Profiles requested: {len(summary.get('profiles_requested', []))}",
        f"Profiles succeeded: {totals.get('profiles_succeeded', 0)}",
        f"Profiles failed: {totals.get('profiles_failed', 0)}",
        f"Companies processed: {totals.get('companies_processed', 0)}",
        f"Jobs scraped: {totals.get('jobs_scraped', 0)}",
        f"Jobs matched role filter: {totals.get('jobs_matched_role_filter', 0)}",
        f"Jobs inserted: {totals.get('jobs_inserted', 0)}",
        f"High-quality inserted (>=4.0): {totals.get('high_quality_inserted', 0)}",
        f"Duplicates skipped: {totals.get('duplicates_skipped', 0)}",
        f"Errors: {totals.get('errors', 0)}",
    ]
    return "\n".join(lines)


def _profile_email(profile_id: str) -> tuple[str, str]:
    profile = load_profile(user_id=profile_id)
    display_name = str(profile.get("display_name", profile_id)).strip() or profile_id
    email = str(profile.get("notification_email", "")).strip()
    return display_name, email


def _send_profile_summaries(summary: dict[str, Any], started_utc: datetime, ended_utc: datetime) -> int:
    sent = 0
    for run in summary.get("profile_runs", []):
        profile_id = str(run.get("profile_id", "")).strip()
        if not profile_id:
            continue
        display_name, recipient = _profile_email(profile_id)
        if not recipient:
            continue
        status = str(run.get("status", "unknown")).strip().lower()
        detail = run.get("summary", {}) or {}

        new_jobs = int(detail.get("jobs_inserted", 0))
        high_quality = int(detail.get("high_quality_inserted", 0))
        duplicates = int(detail.get("duplicates_skipped", 0))
        errors = int(detail.get("errors", 0))

        subject = f"[PM Copilot] Production crawl update - {display_name}"
        body = (
            f"Hi {display_name},\n\n"
            "Your production crawl update is ready.\n\n"
            f"Profile: {profile_id}\n"
            f"Started (UTC): {started_utc.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Ended (UTC): {ended_utc.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Status: {status}\n\n"
            f"New listings added: {new_jobs}\n"
            f"High-quality listings (fit >= 4.0): {high_quality}\n"
            f"Duplicates skipped: {duplicates}\n"
            f"Errors: {errors}\n\n"
            "Open your Streamlit dashboard for full details."
        )
        if _send_email(subject=subject, body=body, email_to=recipient):
            sent += 1
    return sent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hourly crawl with optional start/1h/end email notifications.")
    parser.add_argument("--companies-csv", default="config/target_companies.csv")
    parser.add_argument("--linkedin-csv", default="config/linkedin_jobs.csv")
    parser.add_argument("--manual-jobs-csv", default="config/manual_jobs.csv")
    parser.add_argument("--db-path", default="data/jobs.db")
    parser.add_argument("--profiles", default="")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--summary-path", default="outputs/hourly_summary.json")
    parser.add_argument(
        "--use-profile-sources",
        default="true",
        help="Use per-profile CSV files under config/users/<profile>/ (true/false).",
    )
    parser.add_argument(
        "--midpoint-seconds",
        type=int,
        default=3600,
        help="Send in-progress email after this many seconds if crawl still running.",
    )
    parser.add_argument(
        "--disable-notifications",
        action="store_true",
        help="Disable all workflow notification emails.",
    )
    parser.add_argument(
        "--disable-profile-summary-emails",
        action="store_true",
        help="Disable per-profile summary emails.",
    )
    return parser


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    args = build_parser().parse_args()
    profiles = _parse_profiles(args.profiles)
    started_utc = datetime.now(timezone.utc)
    run_label = started_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    profile_text = ", ".join(profiles) if profiles else "all profiles"

    notify = not args.disable_notifications

    if notify:
        _send_email(
            subject=f"[PM Copilot] Crawl started ({run_label})",
            body=(
                "Hourly crawl has started.\n\n"
                f"Started: {run_label}\n"
                f"Profiles: {profile_text}\n"
                f"DB: {args.db_path}\n"
                f"Summary target: {args.summary_path}\n"
            ),
        )

    done_event = threading.Event()
    midpoint_sent = {"value": False}

    def midpoint_notifier() -> None:
        if done_event.wait(timeout=max(1, int(args.midpoint_seconds))):
            return
        midpoint_sent["value"] = True
        if notify:
            _send_email(
                subject="[PM Copilot] Crawl still running (1-hour update)",
                body=(
                    "Crawl is still running after 1 hour.\n\n"
                    f"Started: {run_label}\n"
                    f"Profiles: {profile_text}\n"
                    "No action needed; final summary will be emailed when complete."
                ),
            )

    watcher = threading.Thread(target=midpoint_notifier, daemon=True)
    watcher.start()

    summary: dict[str, Any] | None = None
    error_text = ""
    try:
        summary = run_hourly(
            companies_csv=args.companies_csv,
            linkedin_csv=args.linkedin_csv,
            manual_jobs_csv=args.manual_jobs_csv,
            db_path=args.db_path,
            profiles=profiles,
            timeout=int(args.timeout),
            use_profile_sources=_parse_bool(args.use_profile_sources),
            summary_path=args.summary_path,
        )
    except Exception as exc:  # pragma: no cover - surfaced in workflow logs
        error_text = str(exc)
        raise
    finally:
        done_event.set()
        watcher.join(timeout=1.0)

        ended_utc = datetime.now(timezone.utc)
        duration_minutes = round((ended_utc - started_utc).total_seconds() / 60.0, 2)

        if notify:
            if summary:
                body = (
                    "Hourly crawl completed.\n\n"
                    f"Started: {started_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Ended: {ended_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Duration (minutes): {duration_minutes}\n"
                    f"Profiles: {profile_text}\n"
                    f"Midpoint email sent: {midpoint_sent['value']}\n\n"
                    "Summary:\n"
                    f"{_format_totals(summary)}\n"
                )
                _send_email(subject="[PM Copilot] Crawl finished (summary)", body=body)
                if not args.disable_profile_summary_emails:
                    sent_count = _send_profile_summaries(summary=summary, started_utc=started_utc, ended_utc=ended_utc)
                    print(f"Profile summary emails sent: {sent_count}")
            else:
                body = (
                    "Hourly crawl failed.\n\n"
                    f"Started: {started_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Ended: {ended_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Duration (minutes): {duration_minutes}\n"
                    f"Profiles: {profile_text}\n"
                    f"Error: {error_text or 'See workflow logs'}\n"
                )
                _send_email(subject="[PM Copilot] Crawl failed", body=body)

    if summary is not None:
        summary_path = Path(args.summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
