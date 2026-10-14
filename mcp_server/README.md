# Campus Customs MCP Server

This folder holds the shop's tool server. It is built with **FastMCP**, a Python library for writing Model Context Protocol (MCP) servers. MCP is a standard way for an AI agent to discover and call tools.

Every Campus Customs agent works the open tickets through these tools: Boss, Inventory, Accounting, Facilities, and Customer Service. So can the vibe coder (Claude Code) while the project is being built. Nobody starts this server by hand during normal use:
- The FastAPI backend will attach it in-process, as in the Lecture 9 build.
- Claude Code starts it from `.mcp.json` at the project root.

## Database

Every tool works on `data/campus_customs_new.db`, the working copy of the shop's database. The original, `data/campus_customs.db`, is never opened here. Reset before every full run:

```bash
python3 data/reset_db.py
```

The reset script copies the original over the working copy. It then adds three empty tables from `data/schema_additions.sql`: `payment_requests`, `purchase_orders`, and `drafts`. The server also adds them on start-up if they are missing.

The tools return only what the database holds, plus figures worked out from it, such as days overdue (measured from `desk.date_today`) or cash left after the bills. Read tools open the database read-only.

## Payments are simulated, and only a human approves them

A "payment" here is a database update: a `payments` row, a lower `checking` balance, and the bill marked paid. No real money moves. Agents can only call `request_payment`. The functions that pay or reject, `approve_payment_request` and `reject_payment_request`, are plain Python functions in `mcp_server.py`, not MCP tools, so no agent can call them. The human-approval step calls them, and the pay function refuses any payment that would take an account below $0.

## Tools

These 11 tools are all the server has. The agents in `backend/agents/` reach them only through this server, and each agent sees only the tools marked for it.

| Tool | Kind | Tickets it unlocks | Agents that may call it |
|---|---|---|---|
| `list_open_tickets(status="open")` | read | 101, 102, 103 | Boss |
| `get_ticket(ticket_id)` | read | 101, 102, 103 | all five |
| `check_stock(sku, size=None, qty_needed=None)` | read | 101, 103 | Inventory, Accounting, Customer Service |
| `list_vendors()` | read | 101, 103 | Inventory, Accounting, Customer Service |
| `get_bills_due()` | read | 101, 102, 103 | Boss, Accounting, Facilities |
| `quote_price(sku, qty, discount_pct=0, markup_pct=0)` | read | 103 | Accounting |
| `list_payments()` | read | 101, 102 | Boss, Accounting |
| `request_payment(kind, ref_id, requested_by, reason, ticket_id=None)` | write | 101, 102, 103 | Accounting |
| `create_purchase_order(vendor_id, sku, size, qty, created_by, ticket_id=None)` | write | 101, 103 | Inventory |
| `save_draft(ticket_id, recipient, body, author)` | write | 101, 103 | Customer Service |
| `update_ticket(ticket_id, status, note, author)` | write | 101, 102, 103 | Boss |

`request_payment` flags `below_cash_floor` when the $200 floor would be crossed. No agent can call the two human-only functions, `approve_payment_request` and `reject_payment_request`.

`output/harness.md` explains what each tool returns and why it helps with each ticket.

## Setup

The whole project uses one Python environment at the project root (see the root `README.md`):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running it by hand (only for testing)

From the project root:

```bash
.venv/bin/python mcp_server/server.py          # stdio, the way Claude Code connects
.venv/bin/python mcp_server/server.py --http   # or HTTP at http://127.0.0.1:8001/mcp
```

Nobody needs to start it for normal use. The FastAPI backend attaches it in-process, and Claude Code starts it from `.mcp.json`.

## Connecting Claude Code

`.mcp.json` at the project root registers the server as `campus-customs`. Open Claude Code in the project root and approve the server when it asks. Its tools then appear with the prefix `mcp__campus-customs__`.

## Smoke test

```bash
.venv/bin/python mcp_server/smoke_test.py
```

Run this from the project root. It works on a scratch copy of the original database, so the working copy is never touched. It calls every tool through `.mcp.json`, the same way Claude Code does, and writes `output/mcp_smoke.json` in two sections:
- `vibe_coder_calls`: the calls Claude Code made itself through its MCP connection, kept in `output/mcp_vibe_coder_calls.json`.
- `script_calls`: this script's steps, each with the prompt, who acted, the tool, its arguments, and its output.

The steps include the refusals the shop's rules demand: a discount below cost, an order from a vendor blocked by an unpaid invoice, a duplicate payment request, a payment that would overdraw checking, and an invalid ticket status.
