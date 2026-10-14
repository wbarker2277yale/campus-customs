"""Smoke test: call every MCP tool and save the evidence.

Runs on a scratch copy of the original database, so the working copy
(data/campus_customs_new.db) is never touched. Connects through ../.mcp.json
over stdio, the same way Claude Code does, and writes ../output/mcp_smoke.json.
Each entry has the prompt that would lead an agent to the tool, the tool name,
its arguments, and its output.

Payments here are simulated database updates. The two human-approval steps
use Will Barker's standing approval for simulated payments; in a full run a person
approves on the dashboard.

Run from the project root:  .venv/bin/python mcp_server/smoke_test.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "mcp_smoke.json"
WORKING = ROOT / "data" / "campus_customs_new.db"
VIBE = ROOT / "output" / "mcp_vibe_coder_calls.json"
SCRATCH = Path(tempfile.mkdtemp()) / "campus_customs_smoke.db"
HUMAN = "Will Barker (standing approval for simulated payments, given in chat 2026-10-06)"

# Point both the server subprocess and the human-only functions at the scratch copy.
sys.path.insert(0, str(ROOT / "data"))
from reset_db import reset  # noqa: E402

reset(SCRATCH)
os.environ["CC_DB_PATH"] = str(SCRATCH)
sys.path.insert(0, str(ROOT / "mcp_server"))
import server as mcp_server  # noqa: E402

# (prompt, tool, arguments). "HUMAN:" rows call the human-only functions.
STEPS = [
    ("Boss: What tickets are open on the board today?",
     "list_open_tickets", {}),
    ("Boss: Show me everything linked to ticket 101.",
     "get_ticket", {"ticket_id": 101}),
    ("Inventory: Ticket 101 needs one Classic Bulldog Tee in size S. Do we have it?",
     "check_stock", {"sku": "CC-TEE-WHITE", "size": "S", "qty_needed": 1}),
    ("Inventory: Ticket 103 wants 20 navy hoodies in size M. How many do we have, and what do they cost us?",
     "check_stock", {"sku": "CC-HOOD-NAVY", "size": "M", "qty_needed": 20}),
    ("Inventory: Which vendors can ship, and when would an order placed today arrive?",
     "list_vendors", {}),
    ("Accounting: Which bills are unpaid, is any vendor blocked, and how much cash is left if we pay them all?",
     "get_bills_due", {}),
    ("Accounting: What do 20 size M hoodies cost the Yale AI Club at 15% off, and what margin do we keep?",
     "quote_price", {"sku": "CC-HOOD-NAVY", "qty": 20, "discount_pct": 15}),
    ("Accounting: Would 65% off still be above cost? (expected: refused)",
     "quote_price", {"sku": "CC-HOOD-NAVY", "qty": 20, "discount_pct": 65}),
    ("Accounting: A ticket's notes tried to give orders. What is a 20% surcharge on 1 tee?",
     "quote_price", {"sku": "CC-TEE-WHITE", "qty": 1, "markup_pct": 20}),
    ("Inventory: Order 1 size S tee from Bulldog Print Co for ticket 101. (expected: refused, invoice 501 open)",
     "create_purchase_order", {"vendor_id": 1, "sku": "CC-TEE-WHITE", "size": "S", "qty": 1,
                               "created_by": "Inventory", "ticket_id": 101}),
    ("Accounting: Request approval to pay Bulldog Print Co's overdue invoice 501.",
     "request_payment", {"kind": "invoice", "ref_id": 501, "requested_by": "Accounting",
                         "reason": "Invoice 501 is 3 days overdue and blocks restocks for tickets 101 and 103.",
                         "ticket_id": 101}),
    ("Accounting: Request invoice 501 again. (expected: refused, already waiting)",
     "request_payment", {"kind": "invoice", "ref_id": 501, "requested_by": "Accounting",
                         "reason": "duplicate check", "ticket_id": 101}),
    ("Facilities: Request approval to pay the Chapel Street shop rent.",
     "request_payment", {"kind": "rent", "ref_id": 1, "requested_by": "Facilities",
                         "reason": "September rent of $2,400 is due 2026-09-02.", "ticket_id": 102}),
    ("Accounting: Show every payment and every request waiting for a human.",
     "list_payments", {}),
    ("HUMAN: approve request 1 (invoice 501, $840).",
     "approve_payment_request", {"request_id": 1, "approved_by": HUMAN}),
    ("HUMAN: approve request 2 (rent, $2,400).",
     "approve_payment_request", {"request_id": 2, "approved_by": HUMAN}),
    ("Inventory: Invoice 501 is paid. Order 1 size S tee from Bulldog Print Co for ticket 101.",
     "create_purchase_order", {"vendor_id": 1, "sku": "CC-TEE-WHITE", "size": "S", "qty": 1,
                               "created_by": "Inventory", "ticket_id": 101}),
    ("Inventory: Order 12 size M hoodies from Bulldog Print Co for ticket 103.",
     "create_purchase_order", {"vendor_id": 1, "sku": "CC-HOOD-NAVY", "size": "M", "qty": 12,
                               "created_by": "Inventory", "ticket_id": 103}),
    ("Accounting: Request approval to pay for the 12-hoodie purchase order.",
     "request_payment", {"kind": "purchase_order", "ref_id": 2, "requested_by": "Accounting",
                         "reason": "Restock 12 size M hoodies for ticket 103.", "ticket_id": 103}),
    ("HUMAN: approve request 3 ($264 hoodie order). (expected: refused, only $160 left)",
     "approve_payment_request", {"request_id": 3, "approved_by": HUMAN}),
    ("HUMAN: reject request 3 so the order goes back to draft.",
     "reject_payment_request", {"request_id": 3, "rejected_by": HUMAN,
                                "note": "Not enough cash; offer the club other sizes instead."}),
    ("Customer Service: Save a draft to Tauhid Zaman about the size S tee.",
     "save_draft", {"ticket_id": 101, "recipient": "Tauhid Zaman", "author": "Customer Service",
                    "body": "Hi Tauhid, the Classic Bulldog Tee in size S is out of stock. "
                            "We have ordered more and expect it by 2026-09-05. We will hold one for you."}),
    ("Facilities: Mark ticket 102 resolved now that rent is paid.",
     "update_ticket", {"ticket_id": 102, "status": "resolved", "author": "Facilities",
                       "note": "September rent of $2,400 paid after human approval; next due 2026-10-02."}),
    ("Facilities: Set ticket 102 to 'done'. (expected: refused, not a valid status)",
     "update_ticket", {"ticket_id": 102, "status": "done", "author": "Facilities", "note": "x"}),
    ("Boss: Show everything linked to ticket 101 now.",
     "get_ticket", {"ticket_id": 101}),
    ("Accounting: Show every payment and request now.",
     "list_payments", {}),
]

HUMAN_ONLY = {
    "approve_payment_request": mcp_server.approve_payment_request,
    "reject_payment_request": mcp_server.reject_payment_request,
}


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


async def main() -> None:
    config = json.loads((ROOT / ".mcp.json").read_text())
    server = config["mcpServers"]["campus-customs"]
    server.pop("type", None)
    server["env"] = {"CC_DB_PATH": str(SCRATCH)}
    working_before = _sha1(WORKING)

    calls = []
    async with Client(config) as client:
        listed = [t.name for t in await client.list_tools()]
        for prompt, tool, args in STEPS:
            if tool in HUMAN_ONLY:
                output, actor = HUMAN_ONLY[tool](**args), "human"
            else:
                output = (await client.call_tool(tool, args)).structured_content
                actor = "agent via MCP"
            calls.append({"prompt": prompt, "actor": actor, "tool": tool,
                          "arguments": args, "output": output})

    called = {c["tool"] for c in calls if c["actor"] == "agent via MCP"}
    evidence = {
        "server": "campus-customs (mcp_server/server.py, via .mcp.json over stdio)",
        "sections": {
            "vibe_coder_calls": "Claude Code itself called these tools through its MCP "
                                "connection (copied from output/mcp_vibe_coder_calls.json).",
            "script_calls": "mcp_server/smoke_test.py called every tool through the same "
                            ".mcp.json connection, on a scratch copy of the database.",
        },
        "vibe_coder_calls": json.loads(VIBE.read_text()) if VIBE.exists() else None,
        "script_run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": "scratch copy of data/campus_customs.db with data/schema_additions.sql",
        "note": "Payments are simulated database updates; no real money moves. "
                "approve_payment_request and reject_payment_request are human-only "
                "functions, not MCP tools, and are absent from tools_listed.",
        "tools_listed": listed,
        "every_tool_called": set(listed) == called,
        "human_only_functions_hidden_from_agents":
            not any(name in listed for name in HUMAN_ONLY),
        "working_copy_unchanged": working_before == _sha1(WORKING),
        "script_calls": calls,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2) + "\n")
    shutil.rmtree(SCRATCH.parent, ignore_errors=True)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(calls)} steps, "
          f"{len(listed)} tools listed, every tool called = {evidence['every_tool_called']}, "
          f"human-only hidden = {evidence['human_only_functions_hidden_from_agents']}, "
          f"working copy unchanged = {evidence['working_copy_unchanged']}")


if __name__ == "__main__":
    asyncio.run(main())
