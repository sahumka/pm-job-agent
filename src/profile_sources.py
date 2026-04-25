from __future__ import annotations

import shutil
from pathlib import Path


def _safe_slug(profile_id: str) -> str:
    text = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in str(profile_id).strip().lower())
    return text.strip("_") or "default"


def profile_source_dir(profile_id: str, root: Path = Path("config/users")) -> Path:
    return root / _safe_slug(profile_id)


def _copy_if_missing(source: Path, dest: Path) -> bool:
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, dest)
    else:
        # Create minimal CSV placeholders if shared source does not exist.
        if dest.name == "target_companies.csv":
            dest.write_text("company_name,careers_url,job_board,user_id,role_keywords,enabled\n", encoding="utf-8")
        elif dest.name in {"linkedin_jobs.csv", "manual_jobs.csv"}:
            dest.write_text("company,title,location,source_url,description,date_posted,user_id,job_board\n", encoding="utf-8")
    return True


def bootstrap_profile_sources(
    profile_id: str,
    companies_csv: str | Path,
    linkedin_csv: str | Path,
    manual_jobs_csv: str | Path,
    root: Path = Path("config/users"),
) -> dict[str, str]:
    """
    Ensure per-profile CSV files exist by copying from shared defaults when missing.
    Returns resolved per-profile paths.
    """
    profile_dir = profile_source_dir(profile_id=profile_id, root=root)
    profile_dir.mkdir(parents=True, exist_ok=True)

    shared_companies = Path(companies_csv)
    shared_linkedin = Path(linkedin_csv)
    shared_manual = Path(manual_jobs_csv)

    profile_companies = profile_dir / "target_companies.csv"
    profile_linkedin = profile_dir / "linkedin_jobs.csv"
    profile_manual = profile_dir / "manual_jobs.csv"

    _copy_if_missing(shared_companies, profile_companies)
    _copy_if_missing(shared_linkedin, profile_linkedin)
    _copy_if_missing(shared_manual, profile_manual)

    return {
        "companies_csv": str(profile_companies),
        "linkedin_csv": str(profile_linkedin),
        "manual_jobs_csv": str(profile_manual),
    }


def resolve_sources_for_profile(
    profile_id: str,
    companies_csv: str | Path,
    linkedin_csv: str | Path,
    manual_jobs_csv: str | Path,
    use_profile_sources: bool = True,
    root: Path = Path("config/users"),
) -> dict[str, str]:
    if not use_profile_sources:
        return {
            "companies_csv": str(companies_csv),
            "linkedin_csv": str(linkedin_csv),
            "manual_jobs_csv": str(manual_jobs_csv),
        }
    return bootstrap_profile_sources(
        profile_id=profile_id,
        companies_csv=companies_csv,
        linkedin_csv=linkedin_csv,
        manual_jobs_csv=manual_jobs_csv,
        root=root,
    )
