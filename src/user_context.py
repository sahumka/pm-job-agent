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
    normalized = dict(DEFAULT_CONTEXT)
    normalized.update(context)
    normalized["user_id"] = _slugify(user_id)

    path = profile_path(normalized["user_id"], root=root)
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
                return normalized

    return load_legacy_preferences()
