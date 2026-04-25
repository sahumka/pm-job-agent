from __future__ import annotations

import re
from urllib.parse import urlparse


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def _tokenize(items: list[str]) -> list[str]:
    return [item.strip().lower() for item in items if item and item.strip()]


def _extract_salary_signals(text: str) -> list[int]:
    """Extract salary-like values from text and normalize to annual USD-ish integers."""
    values: list[int] = []
    patterns = [
        r"\$?\s*([0-9]{2,3})\s*[kK]\+?",         # 180k
        r"\$?\s*([0-9]{2,3})[, ]000",            # 180,000
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text):
            try:
                n = int(match)
            except ValueError:
                continue
            if n < 1000:
                n = n * 1000
            if 25000 <= n <= 1000000:
                values.append(n)
    return values


def _recommendation(score: float) -> str:
    if score >= 4.0:
        return "Apply"
    if score >= 2.8:
        return "Maybe"
    return "Skip"


def score_job(job: dict[str, str], context: dict[str, object] | None = None) -> dict[str, object]:
    """
    Score out of 5 using a local rule-based model.

    Dimensions:
    - role fit
    - seniority fit
    - domain fit
    - skills match
    - location fit
    - visa signal
    - compensation signal
    - red flags
    """
    context = context or {}
    title = job.get("title", "")
    description = job.get("description", "")
    location = job.get("location", "")
    source_url = job.get("source_url", "")

    combined = f"{title}\n{description}"
    combined_l = combined.lower()
    title_l = title.lower()
    location_l = location.lower()

    score = 0.5
    reasons: list[str] = []
    gaps: list[str] = []
    resume_keywords: list[str] = []
    red_flags: list[str] = []

    # 1) Role fit
    target_roles = _tokenize([str(x) for x in context.get("target_roles", [])]) or _tokenize(
        ["Product Manager", "Senior Product Manager"]
    )
    role_hits = [r for r in target_roles if r in title_l]
    if role_hits:
        score += 1.4
        reasons.append(f"Role fit: matched target role(s) in title ({', '.join(role_hits[:2])}).")
    elif "manager" in title_l and any(token in title_l for token in ["product", "analytics", "finance", "data"]):
        score += 0.8
        reasons.append("Role fit: title is adjacent to target manager roles.")
    else:
        gaps.append("Role fit is weak for configured target roles.")

    # 2) Seniority fit
    target_seniority = _tokenize([str(x) for x in context.get("target_seniority", [])]) or ["mid", "senior"]
    years_exp = int(context.get("years_experience", 0) or 0)
    seniority_map = {
        "entry": ["intern", "junior", "associate", "entry"],
        "mid": ["product manager", "manager"],
        "senior": ["senior", "sr", "lead"],
        "principal": ["principal", "staff", "group product manager"],
    }
    seniority_tokens: list[str] = []
    for band in target_seniority:
        seniority_tokens.extend(seniority_map.get(band, [band]))

    if _contains_any(title_l, seniority_tokens):
        score += 0.7
        reasons.append("Seniority fit: title seniority aligns with preferences.")
    elif years_exp >= 5 and _contains_any(title_l, seniority_map["entry"]):
        score -= 0.6
        gaps.append("Role may be below preferred seniority for experience level.")
    else:
        score += 0.2

    # 3) Domain fit
    domains = _tokenize([str(x) for x in context.get("domains", [])])
    if domains:
        domain_hits = [d for d in domains if d in combined_l]
        if domain_hits:
            score += min(0.8, 0.3 + 0.2 * len(domain_hits))
            reasons.append(f"Domain fit: matched {', '.join(domain_hits[:3])}.")
            resume_keywords.extend(domain_hits[:5])
        else:
            gaps.append("No strong domain keyword overlap found.")
    else:
        # Neutral default when no domain preference is configured
        score += 0.2

    # 4) Skills match
    desired_skills = _tokenize([str(x) for x in context.get("skills", [])])
    if not desired_skills:
        desired_skills = _tokenize(
            [
                "roadmap",
                "stakeholder",
                "experimentation",
                "metrics",
                "sql",
                "analytics",
                "requirements",
            ]
        )
    skill_hits = [skill for skill in desired_skills if skill in combined_l]
    if skill_hits:
        score += min(0.9, 0.15 * len(skill_hits))
        reasons.append(f"Skills match: found {', '.join(skill_hits[:5])}.")
        resume_keywords.extend(skill_hits[:8])
    else:
        gaps.append("Skills overlap is limited.")

    must_have = _tokenize([str(x) for x in context.get("must_have_keywords", [])])
    nice_to_have = _tokenize([str(x) for x in context.get("nice_to_have_keywords", [])])
    if must_have:
        missing_must = [term for term in must_have if term not in combined_l]
        present_must = [term for term in must_have if term in combined_l]
        if present_must:
            score += min(0.5, 0.15 * len(present_must))
            reasons.append(f"Must-have coverage: found {', '.join(present_must[:3])}.")
        if missing_must:
            score -= min(0.7, 0.15 * len(missing_must))
            gaps.append(f"Missing must-have keywords: {', '.join(missing_must[:4])}.")
    if nice_to_have:
        present_nice = [term for term in nice_to_have if term in combined_l]
        if present_nice:
            score += min(0.25, 0.08 * len(present_nice))
            reasons.append(f"Nice-to-have signals present: {', '.join(present_nice[:3])}.")

    # 5) Location fit
    preferred_locations = _tokenize([str(x) for x in context.get("preferred_locations", [])]) or ["remote us"]
    excluded_locations = _tokenize([str(x) for x in context.get("excluded_locations", [])])
    work_modes = _tokenize([str(x) for x in context.get("work_modes", [])]) or ["remote", "hybrid", "onsite"]

    if any(excl and excl in combined_l for excl in excluded_locations):
        score -= 0.7
        red_flags.append("Location appears in excluded list.")
    elif any(pref in location_l or pref in combined_l for pref in preferred_locations):
        score += 0.6
        reasons.append("Location fit: aligned with preferred locations.")
    elif "remote" in work_modes and "remote" in combined_l:
        score += 0.5
        reasons.append("Location fit: remote-friendly role.")
    else:
        gaps.append("Location fit is uncertain or outside preferences.")

    # 6) Visa signal
    visa_requirements = _tokenize([str(x) for x in context.get("visa_requirements", [])])
    if visa_requirements:
        if _contains_any(combined_l, ["no sponsorship", "cannot sponsor", "not sponsor"]):
            if any(v in ["h1b", "h-1b", "sponsorship", "visa"] for v in visa_requirements):
                score -= 0.8
                red_flags.append("Role indicates no visa sponsorship.")
        elif _contains_any(combined_l, ["sponsorship available", "visa sponsorship"]):
            reasons.append("Visa signal: sponsorship language present.")
            score += 0.2

    # 7) Compensation signal
    comp_min = int(context.get("compensation_min_usd", 0) or 0)
    salary_values = _extract_salary_signals(combined)
    if comp_min > 0 and salary_values:
        max_seen = max(salary_values)
        if max_seen >= comp_min:
            score += 0.3
            reasons.append("Compensation signal meets minimum preference.")
        else:
            score -= 0.4
            gaps.append("Published compensation appears below configured minimum.")
    elif comp_min > 0:
        gaps.append("Compensation not clearly listed.")

    # 8) Red flags
    avoid_keywords = _tokenize([str(x) for x in context.get("avoid_keywords", [])])
    red_flag_terms = avoid_keywords + ["commission-only", "unpaid", "urgent immediate start", "night shift only"]
    flagged = [term for term in red_flag_terms if term in combined_l]
    if flagged:
        score -= min(1.0, 0.25 * len(flagged))
        red_flags.extend(flagged[:4])

    # Small board confidence bump
    host = urlparse(source_url).netloc.lower()
    if any(part in host for part in ["greenhouse", "lever", "ashby"]):
        score += 0.2

    score = max(0.0, min(5.0, round(score, 2)))
    recommendation = _recommendation(score)
    unique_keywords = sorted({k.strip() for k in resume_keywords if k.strip()})
    score_reason = " ".join(reasons) if reasons else "Limited signal from extracted text."
    if red_flags:
        score_reason = f"{score_reason} Red flags: {', '.join(sorted(set(red_flags)))}."

    return {
        "fit_score": score,
        "recommendation": recommendation,
        "score_reason": score_reason,
        "gaps": gaps,
        "resume_keywords": unique_keywords,
        "tailoring_advice": (
            "Highlight only real, verifiable PM outcomes and naturally mirror relevant JD keywords."
        ),
    }


def compact_text(text: str, max_len: int = 4000) -> str:
    """Normalize whitespace and keep descriptions manageable for storage."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."
