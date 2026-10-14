# Campus Customs Multi-Agent Operations

Campus Customs is a campus apparel shop run by a team of five AI agents: Boss, Inventory, Accounting, Facilities, and Customer Service. They work the shop's open tickets: customer orders, rent, and discount requests. A human watches them on a React board and approves every payment.

The system has three parts that talk to each other:
- **MCP server** (`mcp_server/server.py`): built with FastMCP. Its 11 tools are the only way the agents and the board read or change the shop's database.
- **FastAPI backend** (`backend/`): the five PydanticAI agents, which all use `gpt-6-luna` through Portkey, plus the routes the board calls.
- **React board** (`frontend/`): built with React, Vite, and TypeScript. It shows the tickets, the agents at work, payment approvals, and the checking balance.

## Setup (once)

You need Python 3.12 or newer, Node.js 20 or newer, and a Portkey API key.

```bash
# 1. Secrets: copy the example and put your Portkey key in it (never commit .env)
cp .env.example .env

# 2. Python: one environment for the MCP server and the backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. The board
cd frontend && npm install && cd ..
```

## Copy the original database to the working copy (for a clean run)

`data/campus_customs.db` is the original shop and is never changed. Every tool works on the working copy, `data/campus_customs_new.db`. To start clean, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

`python3 data/reset_db.py` does the same copy, then adds the three empty tables the tools need: `payment_requests`, `purchase_orders`, and `drafts`. The MCP server also adds them on start-up if they are missing.

## Start the MCP server

The backend attaches the MCP server in-process, so the board needs no separate MCP terminal. To run it on its own, for a vibe coder or for testing, use this command from the project root:

```bash
.venv/bin/python mcp_server/server.py          # stdio (how Claude Code connects, via .mcp.json)
.venv/bin/python mcp_server/server.py --http   # or HTTP at http://127.0.0.1:8001/mcp
```

`.mcp.json` registers it for Claude Code as `campus-customs`. Run `.venv/bin/python mcp_server/smoke_test.py` to test every tool on a scratch copy of the database; it writes `output/mcp_smoke.json`.

## Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

The backend serves http://localhost:8000. Its routes are listed in `output/harness.md`. It allows the Vite page's origin (`localhost:5173`, or any local port).

## Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. It has five parts:
- The **Docket** lists the three tickets. Set the order with ▲ ▼, then click **Work this ticket** or **Work all, in this order**.
- The **Common Room** shows each agent speaking, delegating, and calling tools, live.
- **Awaiting Your Signature** holds every payment until you click **Approve** or **Decline**.
- The **checking tag** at the top shows the balance against the $200 floor.
- **Restore opening day**, at the bottom, resets the shop.

## Reset the database before a full three-ticket run

Always start a full run from the original values. Either click **Restore opening day** on the board, or run:

```bash
python3 data/reset_db.py
```

Then click **Work all, in this order**, approve the payments when they appear, and click **Work all** again so Boss can see the approvals and mark the tickets resolved. Every agent-loop step, approval, and reset is appended to `output/audit_trail.json`, which is never wiped.

## Layout

```
AI_prompts.md            prompts typed to the vibe coder, by problem
requirements.txt         Python packages (MCP server and backend)
.env.example  .gitignore  .mcp.json
data/                    campus_customs.db (original), campus_customs_new.db (working copy), reset_db.py, schema_additions.sql
mcp_server/              server.py (FastMCP tools), README.md, smoke_test.py
backend/                 main.py (routes), models.py (data types), prompts/ (one per agent), agents/ (team, delegation, audit, config)
frontend/                the React + Vite + TypeScript board
output/                  harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json,
                         resolved_board.html (+ screenshots/), audit_trail.json, github_url.txt
```
