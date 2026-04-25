from __future__ import annotations

from typing import Any


def score_band(fit_score: float) -> tuple[str, str]:
    """Return label and style band for fit score visualization."""
    pct = max(0.0, min(100.0, fit_score * 20.0))
    if pct >= 80:
        return f"{pct:.0f}% | Strong Fit", "strong"
    if pct >= 60:
        return f"{pct:.0f}% | Possible Fit", "medium"
    return f"{pct:.0f}% | Low Fit", "low"


def parse_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    raw = str(value).strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw.strip("[]")
        return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]
    return [x.strip() for x in raw.split(",") if x.strip()]


def sponsorship_signal(text: str) -> str:
    blob = (text or "").lower()
    if "no sponsorship" in blob or "cannot sponsor" in blob:
        return "No Sponsorship"
    if "visa sponsorship" in blob or "sponsorship available" in blob:
        return "Sponsorship Mentioned"
    return "Unknown"


def missing_keywords(job: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    desc = f"{job.get('title','')} {job.get('description','')}".lower()
    must = [str(x).lower().strip() for x in profile.get("must_have_keywords", []) if str(x).strip()]
    return [kw for kw in must if kw not in desc]
