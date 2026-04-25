from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.http_client import build_session


JOB_LINK_HINTS = [
    "job",
    "career",
    "opening",
    "position",
    "apply",
]


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _looks_like_job_link(title: str, href: str) -> bool:
    blob = f"{title} {href}".lower()
    return any(hint in blob for hint in JOB_LINK_HINTS)


def _extract_location(anchor: Tag) -> str:
    container = anchor.parent
    if not container:
        return "Unknown"

    text = _clean(container.get_text(" ", strip=True))
    match = re.search(
        r"(Remote|Seattle|Bellevue|Denver|Boston|United States|USA|[A-Za-z]+,\s*[A-Z]{2})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean(match.group(1))
    return "Unknown"


def scrape_generic_company_jobs(
    company_name: str,
    careers_url: str,
    timeout: int = 20,
) -> list[dict[str, str]]:
    """Scrape job links from a generic careers page."""
    response = build_session().get(careers_url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen_urls: set[str] = set()
    jobs: list[dict[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href:
            continue
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue

        title = _clean(anchor.get_text(" ", strip=True))
        source_url = urljoin(careers_url, href)

        if not title:
            continue
        if not _looks_like_job_link(title, href):
            continue
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)

        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": _extract_location(anchor),
                "source_url": source_url,
                "description": "",
                "date_posted": "",
                "job_board": "generic",
            }
        )

    return jobs
