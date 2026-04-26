from __future__ import annotations

from pathlib import Path

from src.user_context import (
    get_profile_status,
    list_crawl_enabled_profiles,
    load_profile,
    save_profile,
    set_active_user,
    set_profile_crawl_active,
)


def test_save_and_load_profile(tmp_path: Path) -> None:
    users_dir = tmp_path / "users"
    active_path = tmp_path / "active_user.txt"

    saved = save_profile(
        {
            "user_id": "wife_pm",
            "display_name": "Wife PM",
            "target_roles": ["Product Manager"],
            "preferred_locations": ["Remote US"],
            "setup_completed": True,
        },
        root=users_dir,
    )
    assert saved.exists()

    set_active_user("wife_pm", path=active_path)
    loaded = load_profile(user_id="wife_pm", root=users_dir)

    assert loaded["user_id"] == "wife_pm"
    assert "Product Manager" in loaded["target_roles"]
    assert loaded["crawl_active"] is True


def test_profile_can_be_toggled_inactive(tmp_path: Path) -> None:
    users_dir = tmp_path / "users"
    save_profile(
        {
            "user_id": "shiven_analytics",
            "display_name": "Shiven",
            "target_roles": ["Product Analytics Manager"],
            "setup_completed": True,
        },
        root=users_dir,
    )
    assert list_crawl_enabled_profiles(users_dir) == ["shiven_analytics"]
    assert set_profile_crawl_active("shiven_analytics", False, root=users_dir) is True
    assert list_crawl_enabled_profiles(users_dir) == []


def test_get_profile_status_missing_profile_does_not_fallback(tmp_path: Path) -> None:
    users_dir = tmp_path / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    save_profile(
        {
            "user_id": "tanya_product",
            "display_name": "Tanya",
            "target_roles": ["Product Manager"],
            "setup_completed": True,
            "crawl_active": True,
        },
        root=users_dir,
    )

    status = get_profile_status("shiven_analytics", root=users_dir)
    assert status["user_id"] == "shiven_analytics"
    assert status["configured"] is False
    assert status["crawl_active"] is False

