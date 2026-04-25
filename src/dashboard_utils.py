from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime
from typing import Any

STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "been",
    "being",
    "build",
    "from",
    "have",
    "into",
    "more",
    "must",
    "our",
    "that",
    "their",
    "this",
    "with",
    "will",
    "you",
    "your",
}

KNOWN_PHRASES = [
    "product strategy",
    "product roadmap",
    "stakeholder management",
    "cross functional",
    "go to market",
    "machine learning",
    "data analysis",
    "financial modeling",
    "variance analysis",
    "a b testing",
    "sql",
    "forecasting",
    "budgeting",
    "metrics",
    "experimentation",
    "platform",
]


def split_csv_string(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


def suggest_keywords_from_sample_jds(text: str, top_n: int = 15) -> list[str]:
    """Extract helpful keyword suggestions from pasted sample JDs."""
    normalized = re.sub(r"[^a-zA-Z0-9\s/+.-]", " ", text.lower())
    normalized = normalized.replace("a/b", "a b")
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9+.-]{2,}", normalized) if w not in STOPWORDS]

    counts = Counter(words)
    suggestions = [word for word, count in counts.most_common(top_n * 2) if count >= 2]

    for phrase in KNOWN_PHRASES:
        if phrase in normalized and phrase not in suggestions:
            suggestions.insert(0, phrase)

    ordered: list[str] = []
    seen: set[str] = set()
    for term in suggestions:
        clean = term.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
        if len(ordered) >= top_n:
            break
    return ordered


def parse_date_str(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def funnel_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    total = float(len(rows))
    by_status = Counter(str(row.get("status", "New")) for row in rows)
    applied_pipeline = float(
        by_status.get("Applied", 0) + by_status.get("Interview", 0) + by_status.get("Offer", 0) + by_status.get("Rejected", 0)
    )
    interviews = float(by_status.get("Interview", 0) + by_status.get("Offer", 0))
    offers = float(by_status.get("Offer", 0))

    return {
        "total": total,
        "new": float(by_status.get("New", 0)),
        "interested": float(by_status.get("Interested", 0)),
        "applied": float(by_status.get("Applied", 0)),
        "interview": float(by_status.get("Interview", 0)),
        "offer": offers,
        "rejected": float(by_status.get("Rejected", 0)),
        "skip": float(by_status.get("Skip", 0)),
        "apply_rate_pct": round((applied_pipeline / total * 100.0), 1) if total else 0.0,
        "interview_rate_from_applied_pct": round((interviews / applied_pipeline * 100.0), 1) if applied_pipeline else 0.0,
        "offer_rate_from_interview_pct": round((offers / interviews * 100.0), 1) if interviews else 0.0,
    }


def follow_up_queue(rows: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    now = today or date.today()
    queue: list[dict[str, Any]] = []

    for row in rows:
        status = str(row.get("status", "New"))
        if status in {"Offer", "Rejected", "Skip"}:
            continue

        reason = ""
        due_date = parse_date_str(str(row.get("follow_up_date", "")))
        if due_date and due_date <= now:
            reason = f"Follow-up due ({due_date.isoformat()})"
        elif status == "Interested":
            updated = parse_date_str(str(row.get("updated_at", ""))) or parse_date_str(str(row.get("created_at", "")))
            if updated and (now - updated).days >= 7:
                reason = f"Interested stale for {(now - updated).days} days"
        elif status == "Applied":
            applied = parse_date_str(str(row.get("applied_date", ""))) or parse_date_str(str(row.get("updated_at", "")))
            if applied and (now - applied).days >= 10:
                reason = f"Applied follow-up overdue ({(now - applied).days} days)"

        if reason:
            item = dict(row)
            item["follow_up_reason"] = reason
            queue.append(item)

    queue.sort(key=lambda x: str(x.get("follow_up_date", "")) or "9999-12-31")
    return queue
