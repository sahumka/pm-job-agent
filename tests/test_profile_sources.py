from __future__ import annotations

from pathlib import Path

from src.profile_sources import resolve_sources_for_profile


def test_resolve_sources_for_profile_bootstraps_files(tmp_path: Path) -> None:
    shared_companies = tmp_path / "target_companies.csv"
    shared_linkedin = tmp_path / "linkedin_jobs.csv"
    shared_manual = tmp_path / "manual_jobs.csv"
    shared_companies.write_text("company_name,careers_url,job_board,user_id,role_keywords,enabled\n", encoding="utf-8")
    shared_linkedin.write_text("company,title,location,source_url,description,date_posted,user_id,job_board\n", encoding="utf-8")
    shared_manual.write_text("company,title,location,source_url,description,date_posted,user_id,job_board\n", encoding="utf-8")

    root = tmp_path / "config" / "users"

    paths = resolve_sources_for_profile(
        profile_id="shiven_analytics",
        companies_csv=shared_companies,
        linkedin_csv=shared_linkedin,
        manual_jobs_csv=shared_manual,
        use_profile_sources=True,
        root=root,
    )

    companies_path = Path(paths["companies_csv"])
    linkedin_path = Path(paths["linkedin_csv"])
    manual_path = Path(paths["manual_jobs_csv"])

    assert companies_path.exists()
    assert linkedin_path.exists()
    assert manual_path.exists()
    assert companies_path.parent == root / "shiven_analytics"
    assert companies_path.name == "target_companies.csv"
    assert linkedin_path.name == "linkedin_jobs.csv"
    assert manual_path.name == "manual_jobs.csv"


def test_resolve_sources_for_profile_can_use_shared_paths(tmp_path: Path) -> None:
    shared_companies = tmp_path / "target_companies.csv"
    shared_linkedin = tmp_path / "linkedin_jobs.csv"
    shared_manual = tmp_path / "manual_jobs.csv"
    paths = resolve_sources_for_profile(
        profile_id="tanya_product",
        companies_csv=shared_companies,
        linkedin_csv=shared_linkedin,
        manual_jobs_csv=shared_manual,
        use_profile_sources=False,
    )
    assert paths["companies_csv"] == str(shared_companies)
    assert paths["linkedin_csv"] == str(shared_linkedin)
    assert paths["manual_jobs_csv"] == str(shared_manual)
