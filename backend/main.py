"""Campus Customs backend — FastAPI routes for the React dashboard.

Run from this folder:
  uvicorn main:app --reload --port 8000

Every shop fact comes through the campus-customs MCP server (mcp_server/server.py,
attached in-process), the same tools the agents use. Approve and reject call
the human-only payment functions, which are deliberately not MCP tools.
Runs, approvals, rejections, and resets are all appended to
output/audit_trail.json. Only one agent run happens at a time, and no
approval or rejection ever starts a run on its own.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from collections import defaultdict
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from html import escape  # noqa: E402
import re  # noqa: E402
from fastmcp import Client  # noqa: E402

from agents import audit  # noqa: E402
from agents.config import AUDIT_PATH, MODEL_NAME, ROOT  # noqa: E402
from agents.team import TEAM, new_run_id, open_ticket_ids, run_ticket  # noqa: E402
from models import ReflectionRequest, RejectRequest, ResetRequest, RunAllRequest, TeamDeps  # noqa: E402

for folder in (ROOT / "mcp_server", ROOT / "data"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import server as mcp_server  # noqa: E402  (mcp_server/server.py)
from reset_db import reset as reset_database  # noqa: E402

APPROVER_NAME = os.getenv("APPROVER_NAME", "").strip()
TICKET_STATUSES = mcp_server.TICKET_STATUSES

app = FastAPI(title="Campus Customs Multi-Agent Operations", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    # The Vite dashboard (localhost:5173, or the next free port Vite picks).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------- helpers

async def call_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every shop read goes through the MCP server, never straight to the database."""
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool(name, args or {})
    return result.structured_content


def human_action(action: str, detail: dict[str, Any], ticket_id: int | None = None) -> None:
    deps = TeamDeps(run_id=f"human-{uuid.uuid4().hex[:8]}", ticket_id=ticket_id, chain=["human"])
    audit.append(deps, "human", 0, "human_action", {"action": action, **detail})


class Broadcaster:
    """Fans each audit row of a live run out to every dashboard watching it."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.watchers: list[asyncio.Queue] = []
        self.done = False

    def put_nowait(self, row: dict[str, Any]) -> None:
        self.rows.append(row)
        for q in self.watchers:
            q.put_nowait(row)

    def close(self) -> None:
        self.done = True
        for q in self.watchers:
            q.put_nowait(None)


# One run at a time (Will's answer 5). STATE["run"] holds the run in progress.
STATE: dict[str, Any] = {"run": None}
BROADCASTS: dict[str, Broadcaster] = {}


def busy() -> dict[str, Any] | None:
    run = STATE["run"]
    return run if run and not run["task"].done() else None


def start_run(ticket_ids: list[int]) -> dict[str, Any]:
    if (current := busy()) is not None:
        raise HTTPException(409, f"A run is already going (run {current['run_id']}); wait for it to finish.")
    run_ids = [new_run_id() for _ in ticket_ids]
    group_id = run_ids[0] if len(run_ids) == 1 else f"all-{uuid.uuid4().hex[:8]}"
    caster = BROADCASTS[group_id] = Broadcaster()

    async def work() -> list[dict[str, Any]]:
        audit.live_stream.set(caster)
        results = []
        try:
            for tid, rid in zip(ticket_ids, run_ids):  # oldest first, one at a time
                results.append((await run_ticket(tid, run_id=rid)).model_dump())
        finally:
            caster.close()
        return results

    STATE["run"] = {"run_id": group_id, "ticket_ids": ticket_ids, "run_ids": run_ids,
                    "task": asyncio.create_task(work())}
    return {"run_id": group_id, "ticket_ids": ticket_ids, "run_ids": run_ids,
            "stream": f"/api/runs/{group_id}/stream",
            "note": "The team is working. Watch the stream, or refresh /api/activity."}


# ------------------------------------------------------------- routes

@app.get("/api/health")
async def health():
    """Model, Portkey key, approver name, database, and MCP tool count."""
    async with Client(mcp_server.mcp) as client:
        tools = [t.name for t in await client.list_tools()]
    return {
        "ok": True,
        "model": MODEL_NAME,
        "portkey_key_set": bool(os.getenv("PORTKEY_API_KEY", "").strip()),
        "approver_name": APPROVER_NAME or None,
        "database": mcp_server.DB_PATH.name,
        "mcp_tools": len(tools),
        "agents": list(TEAM),
        "run_in_progress": (busy() or {}).get("run_id"),
    }


@app.get("/api/tickets")
async def tickets():
    """Every ticket and its status (the board), with the shop's date."""
    board, today = [], None
    for status in TICKET_STATUSES:
        data = await call_tool("list_open_tickets", {"status": status})
        today = data["date_today"]
        board += data["tickets"]
    board.sort(key=lambda t: (t["created_at"], t["id"]))
    return {"date_today": today, "count": len(board),
            "tickets": [{"id": t["id"], "subject": t["subject"], "requester": t["requester"],
                         "type": t["type"], "status": t["status"]} for t in board]}


@app.get("/api/tickets/{ticket_id}")
async def ticket(ticket_id: int):
    """One ticket with everything linked to it: stock, invoice, lease, drafts, requests, orders."""
    data = await call_tool("get_ticket", {"ticket_id": ticket_id})
    if data.get("ok") is False:
        raise HTTPException(404, data["refused"])
    return data


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_one(ticket_id: int):
    """Start the agent team on one ticket. Refused while another run is going."""
    data = await call_tool("get_ticket", {"ticket_id": ticket_id})
    if data.get("ok") is False:
        raise HTTPException(404, data["refused"])
    return start_run([ticket_id])


@app.post("/api/run-all", status_code=202)
async def run_all(body: RunAllRequest | None = None):
    """Start the agent team on every open ticket, one at a time: in Will's chosen
    order if given (body {"order": [103, 101, 102]}), otherwise oldest first."""
    ids = await open_ticket_ids()
    if not ids:
        raise HTTPException(409, "No open tickets.")
    if body and body.order:
        unknown = [i for i in body.order if i not in ids]
        if unknown:
            raise HTTPException(400, f"Not open: {unknown}.")
        ids = list(dict.fromkeys(body.order)) + [i for i in ids if i not in body.order]
    return start_run(ids)


@app.get("/api/activity")
async def activity(limit: int = Query(50, ge=1, le=500), run_id: str | None = None):
    """Recent agent activity from the audit trail: who spoke, delegations, tool
    calls and results, newest last. The board polls this to refresh."""
    rows = audit.read_all()
    if run_id:
        run = STATE["run"]
        wanted = set(run["run_ids"]) if run and run["run_id"] == run_id else {run_id}
        rows = [r for r in rows if r["run_id"] in wanted]
    current = busy()
    return {"run_in_progress": current["run_id"] if current else None,
            "steps": rows[-limit:]}


@app.get("/api/runs/{run_id}/stream")
async def stream(run_id: str):
    """Live server-sent events for a run: every audit step as it happens, then 'done'."""
    caster = BROADCASTS.get(run_id)
    if caster is None:
        raise HTTPException(404, f"No live run {run_id}; see /api/runs for past runs.")

    async def events():
        q: asyncio.Queue = asyncio.Queue()
        for row in caster.rows:  # catch up on steps already taken
            q.put_nowait(row)
        if caster.done:
            q.put_nowait(None)
        else:
            caster.watchers.append(q)
        try:
            while (row := await q.get()) is not None:
                yield f"event: step\ndata: {json.dumps(row, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'run_id': run_id})}\n\n"
        finally:
            if q in caster.watchers:
                caster.watchers.remove(q)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/runs")
async def runs():
    """Run history from the audit trail: ticket, start, outcome, tokens, delegations."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audit.read_all():
        if row["kind"] not in ("human_action", "resolution_record"):  # agent runs only
            grouped[row["run_id"]].append(row)
    history = []
    for rid, rows in grouped.items():
        done = next((r for r in rows if r["kind"] == "ticket_done"), None)
        history.append({
            "run_id": rid,
            "ticket_id": rows[0]["ticket_id"],
            "started": rows[0]["time"],
            "finished": done["time"] if done else None,
            "outcome": done["detail"]["stopped"] if done else "running or interrupted",
            "final_status": done["detail"].get("final_status") if done else None,
            "summary": done["detail"].get("summary") if done else None,
            "agents": list(dict.fromkeys(r["agent"] for r in rows)),
            "delegations": sum(1 for r in rows if r["kind"] == "delegation"),
            "total_tokens": max((r["usage"].get("total_tokens", 0) for r in rows), default=0),
            "steps": len(rows),
        })
    return {"runs": sorted(history, key=lambda h: h["started"], reverse=True)}


@app.get("/api/runs/{run_id}")
async def run_detail(run_id: str):
    """Every step of one past run, for replay."""
    rows = [r for r in audit.read_all() if r["run_id"] == run_id]
    if not rows:
        raise HTTPException(404, f"No run {run_id} in the audit trail.")
    return {"run_id": run_id, "steps": rows}


@app.get("/api/payments")
async def payments():
    """Payments made and payment requests (pending ones get Approve/Reject buttons)."""
    return await call_tool("list_payments")


@app.post("/api/payments/{request_id}/approve")
async def approve(request_id: int):
    """Will approves one simulated payment (an invoice, rent, or a purchase order).
    Refused below $0; starts no run."""
    if not APPROVER_NAME:
        raise HTTPException(500, "APPROVER_NAME is not set in .env.")
    result = mcp_server.approve_payment_request(request_id, APPROVER_NAME)
    human_action("approve_payment", {"request_id": request_id, "result": result})
    if result.get("ok") is False:
        raise HTTPException(409, result["refused"])
    return result


@app.post("/api/payments/{request_id}/reject")
async def reject(request_id: int, body: RejectRequest):
    """Will rejects one payment request, with a reason; moves no money and starts no run."""
    if not APPROVER_NAME:
        raise HTTPException(500, "APPROVER_NAME is not set in .env.")
    result = mcp_server.reject_payment_request(request_id, APPROVER_NAME, body.reason)
    human_action("reject_payment", {"request_id": request_id, "reason": body.reason, "result": result})
    if result.get("ok") is False:
        raise HTTPException(409, result["refused"])
    return result


@app.get("/api/cash")
async def cash():
    """The checking balance, unpaid bills, and what is waiting for approval."""
    bills = await call_tool("get_bills_due")
    checking = next((a for a in bills["cash_accounts"] if a["name"] == "checking"), None)
    pending = bills["pending_payment_requests_total"]
    return {
        "date_today": bills["date_today"],
        "checking_balance": checking["balance"] if checking else None,
        "as_of": checking["date"] if checking else None,
        "pending_requests_total": pending,
        "balance_after_pending": (checking["balance"] - pending) if checking else None,
        "cash_floor": mcp_server.CASH_FLOOR,
        "open_invoices": bills["open_invoices"],
        "rent_due": bills["rent_due"],
    }


@app.post("/api/reset")
async def reset(body: ResetRequest):
    """Put the shop back to its original values for a fresh run. Needs confirm=true;
    refused during a run. The audit trail is kept, and the reset is recorded in it."""
    if not body.confirm:
        raise HTTPException(400, "Reset needs confirm=true.")
    if (current := busy()) is not None:
        raise HTTPException(409, f"A run is going (run {current['run_id']}); reset after it finishes.")
    await asyncio.to_thread(reset_database, mcp_server.DB_PATH)
    human_action("reset_database", {"source": "data/campus_customs.db",
                                    "target": f"data/{mcp_server.DB_PATH.name}",
                                    "audit_trail_kept": str(AUDIT_PATH.name)})
    return {"ok": True, "note": "Shop reset to its original values. The audit trail was kept."}


# ------------------------------------------------------------- reflection page

OUTPUT = ROOT / "output"
DESK = OUTPUT / "desk_tickets.html"


@app.post("/api/reflection")
async def save_reflection(body: ReflectionRequest):
    """Save Will's reflection: into output/reflection.md and into the Reflection tab
    of output/desk_tickets.html (between the REFLECTION markers)."""
    text = body.text.strip()
    (OUTPUT / "reflection.md").write_text("# Reflection (Will Barker, in his own words)\n\n" + text + "\n")
    paras = "".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", text))
    block = (f'<!--REFLECTION--><div class="box reflection-saved"><span class="label">Will’s reflection — in his own words</span>'
             f'{paras}</div><!--/REFLECTION-->')
    html = DESK.read_text()
    html = re.sub(r"<!--REFLECTION-->.*?<!--/REFLECTION-->", lambda _: block, html, flags=re.S)
    DESK.write_text(html)
    human_action("save_reflection", {"characters": len(text)})
    return {"ok": True, "saved_to": ["output/reflection.md", "output/desk_tickets.html"]}


# Serves the output pages (e.g. /output/desk_tickets.html#reflection) so the
# Reflection tab can save through the route above.
app.mount("/output", StaticFiles(directory=OUTPUT, html=True), name="output")
