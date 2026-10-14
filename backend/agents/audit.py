"""Audit trail: every agent-loop step is appended to output/audit_trail.json.

The file is one JSON array that only grows. Each append reads the array, adds
one AuditStep, and writes it back atomically; nothing is ever removed. If the
file is ever unreadable it is moved aside (audit_trail.corrupt-<time>.json),
never deleted, and a new array starts.
"""

from __future__ import annotations

import asyncio
import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from pydantic_core import to_json

from agents.config import AUDIT_PATH, AUDIT_PREVIEW_CHARS, MODEL_NAME
from models import AuditStep, TeamDeps

_lock = threading.Lock()

# When a dashboard is streaming a run, each audit row is also put on this queue.
live_stream: ContextVar[asyncio.Queue | None] = ContextVar("live_stream", default=None)


def preview(value: Any, limit: int = AUDIT_PREVIEW_CHARS) -> str:
    text = value if isinstance(value, str) else to_json(value).decode("utf-8", "replace")
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def usage_dict(usage: Any) -> dict[str, int]:
    return {
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "tool_calls": usage.tool_calls,
    }


def append(deps: TeamDeps, agent: str, step: int, kind: str,
           detail: dict[str, Any], usage: Any | None = None) -> dict[str, Any]:
    row = AuditStep(
        time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        run_id=deps.run_id,
        ticket_id=deps.ticket_id,
        agent=agent,
        chain=list(deps.chain),
        depth=len(deps.chain) - 1,
        step=step,
        kind=kind,
        model=MODEL_NAME,
        detail=detail,
        usage=usage_dict(usage) if usage is not None else {},
    ).model_dump()
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows: list[Any] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                rows = loaded if isinstance(loaded, list) else [loaded]
            except json.JSONDecodeError:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
        rows.append(row)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(AUDIT_PATH)
    queue = live_stream.get()
    if queue is not None:
        queue.put_nowait(row)
    return row


def read_all() -> list[dict[str, Any]]:
    """Every audit row, oldest first (read-only)."""
    with _lock:
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            return []
        loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, list) else [loaded]
