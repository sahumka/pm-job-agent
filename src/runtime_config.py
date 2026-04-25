from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv() -> bool:  # type: ignore[misc]
        return False


load_dotenv()


def env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip() or default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def logs_dir() -> Path:
    path = Path(env_str("LOGS_DIR", "logs"))
    path.mkdir(parents=True, exist_ok=True)
    return path
