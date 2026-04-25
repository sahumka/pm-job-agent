from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.http_client import build_session


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _extract_title_from_anchor(anchor: Tag) -> str:
    for heading in anchor.find_all(["h1", "h2", "h3", "h4", "strong", "span"]):
        title = _clean(heading.get_text(" ", strip=True))
        if len(title) >= 3:
            return title
    return _clean(anchor.get_text(" ", strip=True))


def _extract_location_from_anchor(anchor: Tag) -> str:
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


def scrape_ashby_jobs(
    company_name: str,
    careers_url: str,
    timeout: int = 20,
) -> list[dict[str, str]]:
    """
    Scrape Ashby-hosted careers pages.

    Ashby does not have a simple stable unauthenticated listing API for all tenants,
    so this parser uses HTML links as a robust fallback.
    """
    response = build_session().get(careers_url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seen_urls: set[str] = set()
    jobs: list[dict[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href:
            continue
        if not re.search(r"/job(s)?/", href, flags=re.IGNORECASE):
            continue

        source_url = urljoin(careers_url, href)
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)

        title = _extract_title_from_anchor(anchor)
        if not title or len(title) < 3:
            continue

        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": _extract_location_from_anchor(anchor),
                "source_url": source_url,
                "description": "",
                "date_posted": "",
                "job_board": "ashby",
            }
        )

    return jobs
