from __future__ import annotations

import argparse
import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.http_client import build_session
from src.logging_utils import configure_logging

configure_logging("validate_targets")
LOGGER = logging.getLogger(__name__)

@dataclass
class ProbeResult:
    ok: bool
    status_code: int | None
    final_url: str
    error: str


def _normalize_url(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if not text.lower().startswith(("http://", "https://")):
        text = f"https://{text}"
    return text


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def suggestion_candidates(url: str) -> list[str]:
    normalized = _normalize_url(url)
    if not normalized:
        return []
    parsed = urlparse(normalized)
    host = _origin(normalized)
    if not host:
        return []

    path = parsed.path.strip("/")
    candidates = [normalized]

    if path:
        candidates.extend(
            [
                f"{host}/careers",
                f"{host}/jobs",
                f"{host}/careers/jobs",
            ]
        )
    else:
        candidates.extend(
            [
                f"{host}/careers",
                f"{host}/jobs",
                f"{host}/careers/jobs",
            ]
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def probe_url(url: str, timeout: int = 8) -> ProbeResult:
    normalized = _normalize_url(url)
    if not normalized:
        return ProbeResult(ok=False, status_code=None, final_url="", error="empty_url")

    try:
        resp = build_session().get(
            normalized,
            timeout=timeout,
            allow_redirects=True,
        )
        ok = 200 <= int(resp.status_code) < 400
        return ProbeResult(
            ok=ok,
            status_code=int(resp.status_code),
            final_url=str(resp.url or normalized),
            error="",
        )
    except Exception as exc:  # pragma: no cover - network errors are environment-specific
        return ProbeResult(ok=False, status_code=None, final_url=normalized, error=str(exc))


def validate_row(row: dict[str, str], timeout: int = 8, try_suggestions: bool = True) -> dict[str, Any]:
    company = str(row.get("company_name", "")).strip()
    original_url = _normalize_url(str(row.get("careers_url", "")))
    initial = probe_url(original_url, timeout=timeout)

    outcome = "failed"
    if initial.ok:
        if initial.final_url.rstrip("/") != original_url.rstrip("/"):
            outcome = "redirected"
        else:
            outcome = "valid"

    suggested_url = ""
    suggested_status = ""
    best_url = initial.final_url if initial.ok else original_url

    if not initial.ok and try_suggestions:
        for candidate in suggestion_candidates(original_url):
            if candidate.rstrip("/") == original_url.rstrip("/"):
                continue
            probe = probe_url(candidate, timeout=timeout)
            if probe.ok:
                suggested_url = probe.final_url
                suggested_status = f"{probe.status_code}"
                best_url = probe.final_url
                outcome = "suggested_fix"
                break

    return {
        "company_name": company,
        "careers_url": original_url,
        "best_url": best_url,
        "outcome": outcome,
        "http_status": initial.status_code if initial.status_code is not None else "",
        "final_url": initial.final_url,
        "error": initial.error,
        "suggested_url": suggested_url,
        "suggested_status": suggested_status,
        "job_board": str(row.get("job_board", "")).strip(),
        "user_id": str(row.get("user_id", "")).strip(),
        "role_keywords": str(row.get("role_keywords", "")).strip(),
        "enabled": str(row.get("enabled", "true")).strip() or "true",
    }


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {str(k).strip(): str(v or "").strip() for k, v in row.items()}
            if not normalized.get("company_name") or not normalized.get("careers_url"):
                continue
            rows.append(normalized)
        return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and clean target company careers URLs.")
    parser.add_argument("--input-csv", default="config/target_companies.csv", help="Input targets CSV")
    parser.add_argument("--output-dir", default="outputs/url_validation", help="Output directory")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout seconds per request")
    parser.add_argument("--max-workers", type=int, default=32, help="Thread pool size")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to validate (0 = all)")
    parser.add_argument("--no-suggestions", action="store_true", help="Disable fallback URL suggestions")
    return parser


def run_validation(
    input_csv: str,
    output_dir: str,
    timeout: int = 8,
    max_workers: int = 32,
    limit: int = 0,
    try_suggestions: bool = True,
) -> dict[str, Any]:
    rows = load_rows(Path(input_csv))
    if limit > 0:
        rows = rows[:limit]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = [executor.submit(validate_row, row, timeout, try_suggestions) for row in rows]
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: (r.get("company_name", "").lower(), r.get("careers_url", "")))

    valid_rows = [r for r in results if r["outcome"] in {"valid", "redirected", "suggested_fix"}]
    failed_rows = [r for r in results if r["outcome"] == "failed"]

    reusable_targets: list[dict[str, Any]] = []
    for r in valid_rows:
        reusable_targets.append(
            {
                "company_name": r["company_name"],
                "careers_url": r["best_url"] or r["careers_url"],
                "job_board": r["job_board"] or "generic",
                "user_id": r["user_id"],
                "role_keywords": r["role_keywords"],
                "enabled": r["enabled"] or "true",
            }
        )

    out_dir = Path(output_dir)
    write_csv(
        out_dir / "validation_report.csv",
        results,
        fieldnames=[
            "company_name",
            "careers_url",
            "best_url",
            "outcome",
            "http_status",
            "final_url",
            "error",
            "suggested_url",
            "suggested_status",
            "job_board",
            "user_id",
            "role_keywords",
            "enabled",
        ],
    )
    write_csv(
        out_dir / "valid_targets.csv",
        reusable_targets,
        fieldnames=["company_name", "careers_url", "job_board", "user_id", "role_keywords", "enabled"],
    )
    write_csv(
        out_dir / "failed_targets.csv",
        failed_rows,
        fieldnames=[
            "company_name",
            "careers_url",
            "outcome",
            "http_status",
            "error",
            "job_board",
            "user_id",
            "role_keywords",
            "enabled",
        ],
    )

    summary = {
        "input_csv": input_csv,
        "output_dir": str(out_dir),
        "rows_checked": len(results),
        "valid": len([r for r in results if r["outcome"] == "valid"]),
        "redirected": len([r for r in results if r["outcome"] == "redirected"]),
        "suggested_fix": len([r for r in results if r["outcome"] == "suggested_fix"]),
        "failed": len(failed_rows),
        "valid_targets_path": str(out_dir / "valid_targets.csv"),
        "failed_targets_path": str(out_dir / "failed_targets.csv"),
        "report_path": str(out_dir / "validation_report.csv"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    LOGGER.info("URL validation summary: %s", summary)
    return summary


def main() -> None:
    args = build_parser().parse_args()
    summary = run_validation(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        timeout=args.timeout,
        max_workers=args.max_workers,
        limit=args.limit,
        try_suggestions=not args.no_suggestions,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
