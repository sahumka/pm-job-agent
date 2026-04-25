from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(slots=True)
class JobRecord:
    """Represents a single job row in the local SQLite database."""

    company: str
    title: str
    location: str
    source_url: str
    job_board: str
    description: str
    date_found: date
    date_posted: Optional[date] = None
    status: str = "New"
    fit_score: Optional[float] = None
    score_reason: Optional[str] = None
    gaps: Optional[str] = None
    resume_keywords: Optional[str] = None
    applied_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
