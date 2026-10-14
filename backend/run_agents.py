"""Run the Campus Customs agent team from the command line.

From backend/:
  .venv/bin/python run_agents.py            # every open ticket, oldest first
  .venv/bin/python run_agents.py 101 103    # only these tickets

Reset first for a full run:  python3 ../data/reset_db.py
Every loop step is appended to ../output/audit_trail.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from agents.team import run_open_tickets, run_ticket  # noqa: E402


async def main(ids: list[int]) -> None:
    runs = [await run_ticket(i) for i in ids] if ids else await run_open_tickets()
    print(json.dumps([r.model_dump() for r in runs], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main([int(a) for a in sys.argv[1:]]))
