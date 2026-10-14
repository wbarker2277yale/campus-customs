# Backend Routes Plan (Problem 7, built in `backend/main.py`)

Will's answers to the Problem 7 questions, one at a time. `backend/main.py` is built from this plan once the questions are done.

1. **Watching a run:** live, step by step. The backend streams each loop step (server-sent events) so the dashboard shows the agents working as they go. Why, in Will's words: "It's more in tune with the spirit" of the assignment, which is to watch the agents at work.
2. **Approving a simulated payment:** Approve and Reject buttons on each waiting request. The approver's name is filled in from `APPROVER_NAME=Will Barker` in `.env` and saved in `payments.approved_by`; Reject asks for a short reason. Why, in Will's words: "Only I am using this."
3. **Resetting the shop:** a Reset button on the dashboard. It asks for confirmation, refuses while a run is in progress, and never clears `output/audit_trail.json`; the reset itself is recorded there. Why, in Will's words: "I don't do terminal."
4. **Where the dashboard's data comes from:** through the MCP server, using the same tools the agents call, so nothing goes around it. The only exception is approve and reject, which call the human-only functions. Why, in Will's words: "Follow the rules."
5. **Run buttons:** a Run button on each ticket and one "Run all open tickets" button (oldest first). Only one run happens at a time; a second click is refused while a run is going. This keeps to the shop's rules: a full run starts from a reset, and the harness limits allow one ticket at a time. (Will: "Follow the rules.")
6. **Past runs:** a run history read from `output/audit_trail.json`, listing each run's ticket, time, outcome, tokens, and delegations. Clicking a run replays its steps in the same view as a live run; this also feeds the Actual sections of `output/desk_tickets.html`. Why, in Will's words: "More in tune with the assignment."
7. **After an approval or rejection:** nothing runs on its own. Will's decision is saved, the ticket stays where Boss left it, and Boss picks up the decision the next time Will clicks Run on that ticket. Why, in Will's words: "I don't want runs I haven't asked for."

**Standing rule (Will: "I don't do terminal"):** everything Will does happens on the dashboard: running tickets, approving or rejecting simulated payments, and resetting. Nothing he needs requires a command. The vibe coder starts and stops the servers.

## Planned routes (from answers 1–7; built — the final list is in `output/harness.md`)

All shop data comes through the `campus-customs` MCP server. Only approve and reject call the human-only functions. Port 8000; the Vite dashboard runs on 5173.

| Route | Does | From answer |
|---|---|---|
| `GET /api/health` | Model (`gpt-6-luna`), whether the Portkey key is set, database found, MCP tool count | — |
| `GET /api/roster` | The five agents, their jobs, and the MCP tools each may call | — |
| `GET /api/board` | Every ticket grouped by status (`list_open_tickets` once per status) | 4 |
| `GET /api/tickets/{id}` | One ticket with its invoice, lease, stock, drafts, payment requests, and purchase orders (`get_ticket`) | 4 |
| `GET /api/cash` | Cash, unpaid bills, and payments (`get_bills_due`, `list_payments`) | 4 |
| `GET /api/vendors` | Vendors, blocks, and arrival dates (`list_vendors`) | 4 |
| `POST /api/run/{ticket_id}` | Run one ticket and stream every loop step live (server-sent events); refused if a run is already going | 1, 5 |
| `POST /api/run/all` | Run every open ticket, oldest first, streaming live; refused if a run is going | 1, 5 |
| `GET /api/runs` | Run history from the audit trail: ticket, time, outcome, tokens, delegations | 6 |
| `GET /api/runs/{run_id}` | Every step of one past run, for replay | 6 |
| `POST /api/payments/{request_id}/approve` | Pay one request; approver from `APPROVER_NAME` in `.env`; starts no run | 2, 7 |
| `POST /api/payments/{request_id}/reject` | Reject one request with a reason; starts no run | 2, 7 |
| `POST /api/reset` | Reset the shop after confirmation; refused during a run; the audit trail is kept | 3 |

**Changes needed elsewhere when this is built:**
- `team.py` gets an event hook, so each audit step can also go to the live stream.
- `models.py` gets a `human_action` audit kind, so approvals, rejections, and resets are written to `output/audit_trail.json` too.
- `.env` gets `APPROVER_NAME=Will Barker`.
