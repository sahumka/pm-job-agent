from __future__ import annotations

from pathlib import Path

from src.user_context import load_profile, save_profile, set_active_user


def test_save_and_load_profile(tmp_path: Path) -> None:
    users_dir = tmp_path / "users"
    active_path = tmp_path / "active_user.txt"

    saved = save_profile(
        {
            "user_id": "wife_pm",
            "display_name": "Wife PM",
            "target_roles": ["Product Manager"],
            "preferred_locations": ["Remote US"],
        },
        root=users_dir,
    )
    assert saved.exists()

    set_active_user("wife_pm", path=active_path)
    loaded = load_profile(user_id="wife_pm", root=users_dir)

    assert loaded["user_id"] == "wife_pm"
    assert "Product Manager" in loaded["target_roles"]

