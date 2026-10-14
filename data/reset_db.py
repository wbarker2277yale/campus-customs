"""Reset the shop: copy the original database over the working copy, then add
the empty tables from schema_additions.sql.

Run from the project root before every full run:  python3 data/reset_db.py
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / "campus_customs.db"
WORKING = HERE / "campus_customs_new.db"
SCHEMA = HERE / "schema_additions.sql"


def reset(working: Path = WORKING) -> None:
    shutil.copyfile(ORIGINAL, working)
    with sqlite3.connect(working) as conn:
        conn.executescript(SCHEMA.read_text())


if __name__ == "__main__":
    reset()
    print(f"Reset {WORKING.name} from {ORIGINAL.name} and added the empty "
          "payment_requests, purchase_orders, and drafts tables.")
