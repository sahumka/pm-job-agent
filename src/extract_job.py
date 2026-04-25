from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import date
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.db import init_db, insert_job
from src.score_job import compact_text, score_job
from src.user_context import load_profile

LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def fetch_html(url: str, timeout: int = 20) -> str:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def _clean(value: str | None, fallback: str = "") -> str:
    if not value:
        return fallback
    return re.sub(r"\s+", " ", value).strip()


def _extract_json_ld_blocks(soup: BeautifulSoup) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = tag.string or tag.get_text(strip=True)
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            blocks.append(parsed)
        elif isinstance(parsed, list):
            blocks.extend(item for item in parsed if isinstance(item, dict))
    return blocks


def _extract_from_json_ld(soup: BeautifulSoup) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _extract_json_ld_blocks(soup):
        item_type = str(item.get("@type", "")).lower()
        if "jobposting" not in item_type:
            continue

        result["title"] = _clean(str(item.get("title", "")))

        hiring_org = item.get("hiringOrganization")
        if isinstance(hiring_org, dict):
            result["company"] = _clean(str(hiring_org.get("name", "")))

        job_loc = item.get("jobLocation")
        if isinstance(job_loc, dict):
            address = job_loc.get("address")
            if isinstance(address, dict):
                locality = _clean(str(address.get("addressLocality", "")))
                region = _clean(str(address.get("addressRegion", "")))
                country = _clean(str(address.get("addressCountry", "")))
                pieces = [p for p in [locality, region, country] if p]
                if pieces:
                    result["location"] = ", ".join(pieces)

        if item.get("description"):
            soup_desc = BeautifulSoup(str(item["description"]), "html.parser")
            result["description"] = _clean(soup_desc.get_text(" ", strip=True))

        if any(result.values()):
            return result

    return result


def _infer_company_from_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if "greenhouse.io" in host:
        match = re.search(r"/([^/]+)/jobs", url)
        if match:
            return match.group(1).replace("-", " ").title()
    if "lever.co" in host:
        parts = urlparse(url).path.strip("/").split("/")
        if parts:
            return parts[0].replace("-", " ").title()
    if "ashbyhq.com" in host:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1].replace("-", " ").title()

    pieces = host.split(".")
    if pieces:
        return pieces[0].replace("-", " ").title()
    return "Unknown Company"


def _infer_job_board(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "greenhouse" in host:
        return "greenhouse"
    if "lever" in host:
        return "lever"
    if "ashby" in host:
        return "ashby"
    return "generic"


def _extract_title(soup: BeautifulSoup) -> str:
    selectors = [
        ("meta", {"property": "og:title"}, "content"),
        ("meta", {"name": "twitter:title"}, "content"),
        ("meta", {"name": "title"}, "content"),
    ]
    for tag_name, attrs, field in selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get(field):
            return _clean(str(tag.get(field)))

    h1 = soup.find("h1")
    if h1:
        return _clean(h1.get_text(" ", strip=True))

    if soup.title and soup.title.string:
        title_text = _clean(soup.title.string)
        for sep in ["|", "-", "@"]:
            if sep in title_text:
                left = _clean(title_text.split(sep)[0])
                if left:
                    return left
        return title_text

    return "Unknown Title"


def _extract_company(soup: BeautifulSoup, url: str, title: str) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:site_name"}),
        soup.find("meta", attrs={"name": "application-name"}),
    ]
    for tag in candidates:
        if tag and tag.get("content"):
            content = _clean(str(tag.get("content")))
            if content and len(content) <= 80:
                return content

    if " at " in title.lower():
        parts = re.split(r"\bat\b", title, flags=re.IGNORECASE)
        if len(parts) >= 2:
            return _clean(parts[-1].split("|")[0].split("-")[0])

    return _infer_company_from_host(url)


def _extract_location(soup: BeautifulSoup, text_blob: str) -> str:
    loc_patterns = [
        r"(Seattle|Bellevue|Denver|Boston|Remote|United States|USA)",
        r"Location\s*[:\-]\s*([A-Za-z ,/\-]+)",
        r"Based in\s*([A-Za-z ,/\-]+)",
    ]

    for pattern in loc_patterns:
        match = re.search(pattern, text_blob, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1))

    loc_tags = soup.find_all(string=re.compile(r"location|remote", re.IGNORECASE))
    for tag in loc_tags[:5]:
        value = _clean(str(tag))
        if value and len(value) <= 120:
            return value

    return "Unknown"


def extract_job_fields(url: str) -> dict[str, str]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    extracted = _extract_from_json_ld(soup)

    title = extracted.get("title") or _extract_title(soup)
    company = extracted.get("company") or _extract_company(soup, url, title)

    main_text = soup.get_text(" ", strip=True)
    location = extracted.get("location") or _extract_location(soup, main_text)

    description = extracted.get("description")
    if not description:
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "li"])]
        description = " ".join([p for p in paragraphs if p])

    description = compact_text(description or main_text)

    return {
        "title": _clean(title, "Unknown Title"),
        "company": _clean(company, "Unknown Company"),
        "location": _clean(location, "Unknown"),
        "description": description,
        "job_board": _infer_job_board(url),
    }


def run_manual_ingest(
    url: str,
    db_path: str = "data/jobs.db",
    user_id: str | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    context = load_profile(user_id=user_id)

    extracted = extract_job_fields(url)
    score = score_job(
        {
            "title": extracted["title"],
            "description": extracted["description"],
            "location": extracted["location"],
            "source_url": url,
        },
        context=context,
    )

    row = {
        "user_id": context["user_id"],
        "company": extracted["company"],
        "title": extracted["title"],
        "location": extracted["location"],
        "source_url": url,
        "job_board": extracted["job_board"],
        "description": extracted["description"],
        "date_found": date.today().isoformat(),
        "status": "New",
        "fit_score": score["fit_score"],
        "score_reason": score["score_reason"],
        "gaps": json.dumps(score["gaps"]),
        "resume_keywords": json.dumps(score["resume_keywords"]),
        "notes": f"Recommendation: {score['recommendation']}",
    }

    inserted = insert_job(row, db_path=db_path)

    return {
        "inserted": inserted,
        "user_id": context["user_id"],
        "display_name": context.get("display_name", context["user_id"]),
        "source_url": url,
        "company": extracted["company"],
        "title": extracted["title"],
        "location": extracted["location"],
        "job_board": extracted["job_board"],
        "fit_score": score["fit_score"],
        "recommendation": score["recommendation"],
        "score_reason": score["score_reason"],
        "gaps": score["gaps"],
        "resume_keywords": score["resume_keywords"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual job ingestion from a URL")
    parser.add_argument("url", help="Job posting URL")
    parser.add_argument(
        "--db-path",
        default="data/jobs.db",
        help="SQLite database path (default: data/jobs.db)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="User profile id (example: wife_pm). If omitted, active/fallback profile is used.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run_manual_ingest(url=args.url, db_path=args.db_path, user_id=args.user_id)
    except requests.RequestException as exc:
        LOGGER.error("Failed to fetch URL: %s", exc)
        raise SystemExit(2) from exc
    except Exception as exc:  # defensive for CLI experience
        LOGGER.exception("Manual ingest failed: %s", exc)
        raise SystemExit(1) from exc

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
