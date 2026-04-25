from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - allow no-deps local fallback
    yaml = None  # type: ignore[assignment]

DEFAULT_CONTEXT = {
    "user_id": "default",
    "display_name": "Default User",
    "notification_email": "",
    "crawl_active": False,
    "target_roles": ["Product Manager"],
    "preferred_locations": ["Remote US"],
    "excluded_locations": [],
    "work_modes": ["remote", "hybrid", "onsite"],
    "years_experience": 0,
    "target_seniority": ["mid", "senior"],
    "domains": [],
    "skills": [],
    "must_have_keywords": [],
    "nice_to_have_keywords": [],
    "avoid_keywords": [],
    "visa_requirements": [],
    "compensation_min_usd": 0,
}


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned or "user"


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def profile_path(user_id: str, root: Path = Path("config/users")) -> Path:
    return root / f"{_slugify(user_id)}.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
        if not isinstance(content, dict):
            return {}
        return content


def save_profile(context: dict[str, Any], root: Path = Path("config/users")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    user_id = str(context.get("user_id", "")).strip() or "user"
    normalized_user = _slugify(user_id)
    path = profile_path(normalized_user, root=root)
    existing = _read_yaml(path)

    normalized = dict(DEFAULT_CONTEXT)
    normalized.update(existing)
    normalized.update(context)
    normalized["user_id"] = normalized_user

    # First setup defaults to crawl-active; later edits preserve explicit choice.
    if "crawl_active" in context:
        normalized["crawl_active"] = _as_bool(context.get("crawl_active"), default=True)
    elif existing:
        normalized["crawl_active"] = _as_bool(existing.get("crawl_active"), default=True)
    else:
        normalized["crawl_active"] = True

    with path.open("w", encoding="utf-8") as handle:
        if yaml is None:
            # Minimal fallback format if PyYAML is unavailable.
            for key, value in normalized.items():
                handle.write(f"{key}: {value}\n")
        else:
            yaml.safe_dump(normalized, handle, sort_keys=False)
    return path


def set_active_user(user_id: str, path: Path = Path("config/active_user.txt")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_slugify(user_id), encoding="utf-8")


def get_active_user(path: Path = Path("config/active_user.txt")) -> str | None:
    if not path.exists():
        return None
    user_id = path.read_text(encoding="utf-8").strip()
    return _slugify(user_id) if user_id else None


def load_legacy_preferences(path: Path = Path("config/search_preferences.yaml")) -> dict[str, Any]:
    """Fallback to pre-multi-user config if no user profile exists yet."""
    raw = _read_yaml(path)
    target_roles = raw.get("target_roles") or ["Product Manager"]
    preferred_locations = raw.get("preferred_locations") or ["Remote US"]
    years = int(raw.get("profile", {}).get("years_pm_experience", 0) or 0)

    legacy = dict(DEFAULT_CONTEXT)
    legacy.update(
        {
            "user_id": "default",
            "display_name": "Legacy Default",
            "target_roles": target_roles,
            "preferred_locations": preferred_locations,
            "years_experience": years,
        }
    )
    return legacy


def load_profile(user_id: str | None = None, root: Path = Path("config/users")) -> dict[str, Any]:
    """Load a profile and always return a usable dictionary."""
    resolved_id = _slugify(user_id) if user_id else get_active_user()

    if resolved_id:
        candidate = _read_yaml(profile_path(resolved_id, root=root))
        if candidate:
            normalized = dict(DEFAULT_CONTEXT)
            normalized.update(candidate)
            normalized["user_id"] = _slugify(str(normalized.get("user_id", resolved_id)))
            normalized["crawl_active"] = _as_bool(normalized.get("crawl_active"), default=False)
            return normalized

    # Auto-load first profile if present.
    if root.exists():
        yaml_files = sorted(root.glob("*.yaml"))
        if yaml_files:
            candidate = _read_yaml(yaml_files[0])
            if candidate:
                normalized = dict(DEFAULT_CONTEXT)
                normalized.update(candidate)
                normalized["user_id"] = _slugify(str(normalized.get("user_id", yaml_files[0].stem)))
                normalized["crawl_active"] = _as_bool(normalized.get("crawl_active"), default=False)
                return normalized

    legacy = load_legacy_preferences()
    legacy["crawl_active"] = _as_bool(legacy.get("crawl_active"), default=False)
    return legacy


def is_profile_configured(profile: dict[str, Any]) -> bool:
    user_id = str(profile.get("user_id", "")).strip()
    display = str(profile.get("display_name", "")).strip()
    target_roles = [str(x).strip() for x in profile.get("target_roles", []) if str(x).strip()]
    return bool(user_id and display and target_roles)


def list_crawl_enabled_profiles(root: Path = Path("config/users")) -> list[str]:
    if not root.exists():
        return []
    enabled: list[str] = []
    for path in sorted(root.glob("*.yaml")):
        profile = load_profile(user_id=path.stem, root=root)
        if is_profile_configured(profile) and _as_bool(profile.get("crawl_active"), default=False):
            enabled.append(str(profile["user_id"]))
    return enabled


def set_profile_crawl_active(user_id: str, active: bool, root: Path = Path("config/users")) -> bool:
    uid = _slugify(user_id)
    path = profile_path(uid, root=root)
    if not path.exists():
        return False
    profile = load_profile(user_id=uid, root=root)
    profile["crawl_active"] = bool(active)
    save_profile(profile, root=root)
    return True


def get_profile_status(user_id: str, root: Path = Path("config/users")) -> dict[str, Any]:
    profile = load_profile(user_id=user_id, root=root)
    return {
        "user_id": str(profile.get("user_id", "")).strip(),
        "configured": is_profile_configured(profile),
        "crawl_active": _as_bool(profile.get("crawl_active"), default=False),
    }
