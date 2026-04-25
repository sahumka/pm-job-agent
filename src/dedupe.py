from __future__ import annotations

from typing import Any


def normalize_text(value: str) -> str:
    """Normalize text to improve duplicate checks."""
    return " ".join(value.strip().lower().split())


def dedupe_key(company: str, title: str, location: str) -> str:
    """Build a stable key for duplicate detection by company+title+location."""
    return "|".join(
        [
            normalize_text(company),
            normalize_text(title),
            normalize_text(location),
        ]
    )


def row_to_dedupe_key(row: dict[str, Any]) -> str:
    """Create dedupe key from a dict-like job row."""
    return dedupe_key(
        str(row.get("company", "")),
        str(row.get("title", "")),
        str(row.get("location", "")),
    )
