from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.http_client import build_session


def _board_token_from_url(careers_url: str) -> str:
    parsed = urlparse(careers_url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if not path_parts:
        raise ValueError(f"Cannot infer Greenhouse board token from URL: {careers_url}")
    return path_parts[0]


def _strip_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def scrape_greenhouse_jobs(
    company_name: str,
    careers_url: str,
    timeout: int = 20,
) -> list[dict[str, str]]:
    """Scrape jobs from a Greenhouse board API."""
    token = _board_token_from_url(careers_url)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

    response = build_session().get(api_url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    jobs: list[dict[str, str]] = []
    for item in payload.get("jobs", []):
        title = str(item.get("title", "")).strip()
        if not title:
            continue

        location = str(item.get("location", {}).get("name", "Unknown")).strip() or "Unknown"
        source_url = str(item.get("absolute_url", "")).strip()
        if not source_url:
            continue

        description = _strip_html(str(item.get("content", "")))
        date_posted = str(item.get("updated_at", "")).strip()
        if date_posted:
            date_posted = re.sub(r"T.*$", "", date_posted)

        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": location,
                "source_url": source_url,
                "description": description,
                "date_posted": date_posted,
                "job_board": "greenhouse",
            }
        )

    return jobs
