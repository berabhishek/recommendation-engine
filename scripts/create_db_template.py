from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine

from app.database import recreate_schema


def main() -> None:
    template_path = Path(os.getenv("DB_TEMPLATE_PATH", "/opt/db-template/recommendation.db"))
    template_path.parent.mkdir(parents=True, exist_ok=True)
    if template_path.exists():
        template_path.unlink()

    engine = create_engine(f"sqlite:///{template_path}")
    recreate_schema(engine, drop_existing=False)


if __name__ == "__main__":
    main()
