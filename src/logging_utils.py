from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.runtime_config import env_bool, logs_dir


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app_name: str = "pmcopilot") -> None:
    root = logging.getLogger()
    if getattr(root, "_pmcopilot_configured", False):
        return

    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    use_json = env_bool("LOG_JSON", default=False)
    fmt = JsonFormatter() if use_json else logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)

    logfile = logs_dir() / f"{app_name}.log"
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    root._pmcopilot_configured = True  # type: ignore[attr-defined]
