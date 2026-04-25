from __future__ import annotations

import json
from pathlib import Path

from src.run_hourly import list_profile_ids, run_hourly


def test_list_profile_ids_reads_enabled_profiles(tmp_path: Path) -> None:
    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    (users_root / "tanya_product.yaml").write_text(
        "user_id: tanya_product\n"
        "display_name: Tanya\n"
        "target_roles:\n"
        "  - Product Manager\n"
        "crawl_active: true\n",
        encoding="utf-8",
    )
    (users_root / "shiven_analytics.yaml").write_text(
        "user_id: shiven_analytics\n"
        "display_name: Shiven\n"
        "target_roles:\n"
        "  - Product Analytics Manager\n"
        "crawl_active: true\n",
        encoding="utf-8",
    )
    assert list_profile_ids(users_root) == ["shiven_analytics", "tanya_product"]


def test_run_hourly_writes_summary(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "jobs.db"
    summary_path = tmp_path / "hourly_summary.json"

    monkeypatch.setattr(
        "src.run_hourly.run_daily",
        lambda **_: {
            "companies_processed": 2,
            "jobs_scraped": 5,
            "jobs_matched_role_filter": 3,
            "jobs_inserted": 2,
            "duplicates_skipped": 1,
            "errors": 0,
        },
    )
    monkeypatch.setattr(
        "src.run_hourly.get_profile_status",
        lambda _pid: {"user_id": "tanya_product", "configured": True, "crawl_active": True},
    )

    out = run_hourly(
        companies_csv=str(tmp_path / "companies.csv"),
        linkedin_csv=str(tmp_path / "linkedin.csv"),
        manual_jobs_csv=str(tmp_path / "manual.csv"),
        db_path=str(db_path),
        profiles=["tanya_product"],
        summary_path=str(summary_path),
    )

    assert out["totals"]["profiles_succeeded"] == 1
    assert out["totals"]["jobs_inserted"] == 2
    assert summary_path.exists()

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["profile_runs"][0]["profile_id"] == "tanya_product"
    assert payload["profile_runs"][0]["status"] == "success"
