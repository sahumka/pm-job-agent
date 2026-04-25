from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.http_client import build_session


def _token_from_url(careers_url: str) -> str:
    parsed = urlparse(careers_url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if not parts:
        raise ValueError(f"Cannot infer Lever company token from URL: {careers_url}")

    if parts[0].lower() == "postings" and len(parts) > 1:
        return parts[1]
    return parts[0]


def _strip_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def _date_from_ms_epoch(value: int | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        return ""
    return dt.date().isoformat()


def scrape_lever_jobs(
    company_name: str,
    careers_url: str,
    timeout: int = 20,
) -> list[dict[str, str]]:
    """Scrape jobs from Lever's public postings API."""
    token = _token_from_url(careers_url)
    api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"

    response = build_session().get(api_url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    jobs: list[dict[str, str]] = []
    for item in payload:
        title = str(item.get("text", "")).strip()
        source_url = str(item.get("hostedUrl", "")).strip()
        if not title or not source_url:
            continue

        categories = item.get("categories", {}) if isinstance(item, dict) else {}
        location = str(categories.get("location", "Unknown")).strip() or "Unknown"

        description_plain = str(item.get("descriptionPlain", "")).strip()
        description_html = str(item.get("description", "")).strip()
        description = description_plain or _strip_html(description_html)

        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": location,
                "source_url": source_url,
                "description": description,
                "date_posted": _date_from_ms_epoch(item.get("createdAt")),
                "job_board": "lever",
            }
        )

    return jobs
