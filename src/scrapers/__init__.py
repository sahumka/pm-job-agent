
from __future__ import annotations

import logging
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)


def detect_job_board(careers_url: str, hint: str | None = None) -> str:
    if hint:
        normalized = hint.strip().lower()
        if normalized in {"greenhouse", "lever", "ashby", "generic"}:
            return normalized

    host = urlparse(careers_url).netloc.lower()
    if "greenhouse" in host:
        return "greenhouse"
    if "lever.co" in host:
        return "lever"
    if "ashbyhq.com" in host:
        return "ashby"
    if "linkedin.com" in host:
        return "linkedin"
    return "generic"


def scrape_company_jobs(
    company_name: str,
    careers_url: str,
    job_board: str | None = None,
    timeout: int = 20,
) -> list[dict[str, str]]:
    board = detect_job_board(careers_url=careers_url, hint=job_board)
    LOGGER.info("Scraping %s via %s", company_name, board)

    try:
        if board == "greenhouse":
            from src.scrapers.greenhouse import scrape_greenhouse_jobs

            return scrape_greenhouse_jobs(company_name=company_name, careers_url=careers_url, timeout=timeout)
        if board == "lever":
            from src.scrapers.lever import scrape_lever_jobs

            return scrape_lever_jobs(company_name=company_name, careers_url=careers_url, timeout=timeout)
        if board == "ashby":
            from src.scrapers.ashby import scrape_ashby_jobs

            return scrape_ashby_jobs(company_name=company_name, careers_url=careers_url, timeout=timeout)
        if board == "linkedin":
            # Online LinkedIn scraping intentionally disabled for compliance.
            from src.scrapers.linkedin import scrape_linkedin_jobs

            return scrape_linkedin_jobs()
        from src.scrapers.generic_company import scrape_generic_company_jobs

        return scrape_generic_company_jobs(company_name=company_name, careers_url=careers_url, timeout=timeout)
    except Exception as exc:
        LOGGER.warning("Scraper failed for %s (%s): %s", company_name, board, exc)
        return []
