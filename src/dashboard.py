from __future__ import annotations

import sys
from pathlib import Path

# Backward-compatible entrypoint.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import main


if __name__ == "__main__":
    main()
