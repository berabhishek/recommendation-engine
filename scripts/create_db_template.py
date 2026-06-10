from __future__ import annotations

import os
from pathlib import Path

from app.migrations import upgrade_database


def main() -> None:
    template_path = Path(os.getenv("DB_TEMPLATE_PATH", "/opt/db-template/recommendation.db"))
    template_path.parent.mkdir(parents=True, exist_ok=True)
    if template_path.exists():
        template_path.unlink()
    upgrade_database(f"sqlite:///{template_path}")


if __name__ == "__main__":
    main()
