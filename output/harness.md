# Campus Customs Harness

The whole system on one page:
1. **Tables:** the shop's data.
2. **MCP tools:** the only way agents and the dashboard touch that data.
3. **Agents:** the five-member team, and how they delegate.
4. **Backend routes:** the FastAPI app the dashboard calls.
5. **Dashboard:** the React board.
6. **Safety:** the guardrails and token limits.
7. **Outputs:** the records each run leaves behind.

# 1. Tables

Every table in `data/campus_customs_new.db`, field by field, with why each field matters. The first nine tables come from the original shop database; the last three are added empty by `data/schema_additions.sql`.

The agents and tools read and write these fields in `data/campus_customs_new.db`. Each line says why the field matters.

## desk
- `date_today` — The shop's "today"; every overdue and due-soon check uses this date, never the real clock.
- `notes` — Free-text notes about the shop day; empty at the start.

## tickets
- `id` — Ticket number that agents, drafts, and approvals refer to.
- `type` — Tells Boss who should take the ticket (`customer_order`, `rent_notice`, `price_override`).
- `requester` — The person or group that any Customer Service draft is addressed to.
- `subject` — Short title shown on the dashboard board.
- `sku` — The product involved; links to `inventory` and `pricing`.
- `size` — Together with `sku`, picks the exact inventory row to check.
- `qty` — Quantity requested; compared with stock to find a shortfall.
- `lease_id` — Links a rent ticket to its lease, for Facilities.
- `invoice_id` — Links a ticket to the vendor invoice that affects it (101 → 501).
- `status` — Where the ticket stands on the board (`open` at the start); updated as agents work.
- `notes` — The original request text, plus a place to record what agents decided.
- `created_at` — When the ticket arrived; sets the order of work.

## inventory
- `sku` — Product ID; part of the key, and joins to `pricing` and `tickets`.
- `name` — Readable product name for drafts and the dashboard.
- `size` — Second part of the key; stock is tracked per size.
- `qty` — Units on hand; 0 or below the request means a restock is needed.
- `location` — Aisle where the item sits in the shop; useful for fulfilment notes.

## pricing
- `sku` — Product ID; joins to `inventory` and `tickets`.
- `unit_cost` — What the shop pays per unit; sets restock cost and the floor for any discount.
- `list_price` — Normal selling price; the starting point for discounts and margin checks.

## vendors
- `id` — Joins to `invoices.vendor_id`, which is how to tell whether a vendor has an unpaid bill.
- `name` — Who to restock from (draft only; no real calls).
- `specialty` — Matches a product to the right vendor (apparel goes to Bulldog Print Co).
- `lead_days` — Days until a restock arrives; used to give customers an ETA.

## invoices
- `id` — Invoice number; a ticket's `invoice_id` points here, and so does a payment's `ref_id`.
- `vendor_id` — The vendor owed; an open invoice here blocks new shipments from that vendor.
- `amount` — Cash needed to pay it off.
- `due_date` — Compared with `desk.date_today` to tell whether the invoice is overdue.
- `status` — `open` means unpaid and the vendor is blocked; changes to paid after an approved payment.
- `description` — What the bill was for (501 was a rush reprint of the size S tee).

## leases
- `id` — Lease number; a ticket's `lease_id` points here, and so does a payment's `ref_id`.
- `space_name` — Which shop space the rent is for.
- `landlord` — Who is paid, and who any Facilities draft is addressed to.
- `monthly_rent` — The amount due each month.
- `next_due` — When rent is due; checked against `date_today`, and moves forward one month after payment.
- `notes` — Lease remarks; empty at the start.

## cash_accounts
- `name` — Account to pay from (only `checking`).
- `balance` — Cash available; the pay tool must refuse any payment larger than this.
- `date` — When the balance was last updated; refreshed when a payment goes out.

## payments
- `id` — Payment record number.
- `kind` — What was paid (for example an invoice or rent); says which table `ref_id` points into.
- `ref_id` — ID of the invoice or lease that was paid.
- `amount` — How much left the account.
- `account` — Which `cash_accounts` row it came from.
- `paid_at` — When the payment was made.
- `approved_by` — The human who approved it. This is required: no payment goes out without a name here.

## payment_requests (added by `data/schema_additions.sql`; starts empty)
- `id`: request number; the dashboard approves or rejects by this ID.
- `kind`: `invoice`, `rent`, or `purchase_order`; says which table `ref_id` points into.
- `ref_id`: the invoice, lease, or purchase order to be paid.
- `ticket_id`: the ticket the payment resolves (501 → ticket 101, rent → ticket 102).
- `amount`: copied from the bill itself, never typed by an agent, so no amount is invented.
- `account`: the cash account to pay from (`checking`).
- `requested_by`: the agent that prepared the payment.
- `reason`: one line telling the human approver why the payment matters.
- `status`: `pending_approval`, `rejected`, or `paid`; nothing moves while pending.
- `requested_at`: the shop date of the request.
- `decided_by`: the human who approved or rejected it.
- `decided_at`: the shop date of the decision.
- `decision_note`: the human's reason, mainly for rejections.
- `payment_id`: the `payments` row written when the request was paid.

## purchase_orders (added; starts empty)
- `id`: order number; a payment request of kind `purchase_order` points here.
- `vendor_id`: the vendor asked to restock; it must have no open invoice.
- `sku`: the product being restocked.
- `size`: the size being restocked.
- `qty`: how many units are ordered.
- `unit_cost`: taken from `pricing` when the order is drafted.
- `total`: `qty` × `unit_cost`; the cash the order will need.
- `ticket_id`: the ticket the restock serves (101 or 103).
- `created_by`: the agent that drafted the order.
- `status`: `draft`, `awaiting_approval`, or `ordered` (set only after the simulated payment).
- `created_at`: the shop date of the draft.
- `expected_arrival`: shop date plus the vendor's `lead_days`; gives Customer Service an ETA.

## drafts (added; starts empty)
- `id`: draft number.
- `ticket_id`: the ticket the message answers.
- `recipient`: who the message is for (a customer, the landlord, or a vendor).
- `body`: the message text.
- `author`: the agent that wrote it.
- `status`: always `draft`; the shop's rules forbid sending.
- `created_at`: the shop date of the draft.

---

# 2. MCP Tools

The tools live in `mcp_server/server.py`, served by FastMCP under the name `campus-customs`. Every tool works on the working copy, `data/campus_customs_new.db`, and adds no data of its own. Payments are simulated: they change rows in the database and move no real money.

The money rule: agents can only **request** a payment. Two plain Python functions in the same file, `approve_payment_request` and `reject_payment_request`, are deliberately **not** MCP tools, so no agent can call them. Only the human-approval step (the dashboard, in a later problem) calls them.

## Read tools

### `list_open_tickets(status="open")`
- **Returns:** every ticket with the given status, oldest first, with the shop's `date_today`.
- **Unlocks:** 101, 102, and 103.
- **Why it helps:** Boss sees each request with the link that decides who takes it: a SKU and size (Inventory, for 101 and 103), a `lease_id` (Facilities, for 102), or an `invoice_id` (Accounting, for 101's link to invoice 501).

### `get_ticket(ticket_id)`
- **Returns:** one ticket with every record it links to: its invoice and vendor, lease, inventory row, pricing, shortfall, drafts, payment requests, and purchase orders.
- **Unlocks:** 101, 102, and 103.
- **Why it helps:** an agent handed ticket 101 gets the size S tee's 0 units, invoice 501's $840 (3 days overdue), and Bulldog Print Co's 5-day lead time in one call instead of three.

### `check_stock(sku, size=None, qty_needed=None)`
- **Returns:** units on hand per size, the aisle, unit cost, list price, and the shortfall when `qty_needed` is given.
- **Unlocks:** 101 and 103.
- **Why it helps:** Inventory learns that ticket 101's size S tee has 0 on hand (short by 1) and that ticket 103's size M hoodie has 8 of the 20 the Yale AI Club wants (short by 12).

### `list_vendors()`
- **Returns:** every vendor with its specialty, lead time, and open invoices; whether it is blocked; and when an order placed today would arrive.
- **Unlocks:** 101 and 103.
- **Why it helps:** Inventory sees that Bulldog Print Co, the only apparel vendor, is blocked by invoice 501, while Elm City Gifts (arrival 2026-09-03) and QuickShip CT (2026-09-01) could ship today.

### `get_bills_due()`
- **Returns:** each open vendor invoice with days overdue and a `vendor_blocked` flag; each lease's rent with days until due; cash on hand; cash left if every bill were paid; and the total already waiting for approval.
- **Unlocks:** 102 directly, and 101 and 103 by showing what blocks them.
- **Why it helps:** Accounting sees that paying invoice 501 ($840) and the rent ($2,400) leaves $160 of the $3,400 in checking, too little for the 12 missing hoodies ($264).

### `quote_price(sku, qty, discount_pct=0, markup_pct=0)`
- **Returns:** the unit price after a discount or a markup, the order total, the margin, the break-even discount, `bulk_eligible` (10 units or more), and `needs_will` (a discount over 20%). It refuses any price at or below cost.
- **Unlocks:** 103.
- **Why it helps:** Accounting can show the Yale AI Club's 20 hoodies at 15% off ($49.30 each, $986 total, a 55% margin) and prove that any discount past 62% would sell below the $22.00 unit cost.

### `list_payments()`
- **Returns:** every payment with its human approver, every payment request, the cash balance, and the total still waiting.
- **Unlocks:** 101 and 102, as proof.
- **Why it helps:** Accounting and the dashboard can show that invoice 501 and the September rent were each paid once, from checking, with a named human approval.

## Write tools

### `request_payment(kind, ref_id, requested_by, reason, ticket_id=None)`
- **Does:** records a payment request with status `pending_approval`, taking the amount from the bill itself. It refuses a bill already paid or already waiting, and flags `below_cash_floor` when paying everything waiting would leave checking under $200.
- **Unlocks:** 101 (invoice 501, $840), 102 (rent, $2,400), and 103 (a purchase order).
- **Why it helps:** Accounting prepares each simulated payment for the human approval the shop's rules require, and sees the cash left if it is approved.

### `create_purchase_order(vendor_id, sku, size, qty, created_by, ticket_id=None)`
- **Does:** drafts a restock order at unit cost with an expected arrival date. It refuses if the vendor still has an open invoice.
- **Unlocks:** 101 (1 size S tee, $8.00) and 103 (up to 12 size M hoodies, $264.00).
- **Why it helps:** Inventory can order missing stock as soon as invoice 501 is paid, and cannot order from Bulldog Print Co before then.

### `save_draft(ticket_id, recipient, body, author)`
- **Does:** saves a message draft on the board and sends nothing.
- **Unlocks:** 101 (to Tauhid Zaman) and 103 (to the Yale AI Club). Ticket 102 gets no draft, because Will writes to the landlord himself.
- **Why it helps:** Customer Service writes the replies, and the shop's rules keep every draft on the board, unsent.

### `update_ticket(ticket_id, status, note, author)`
- **Does:** sets a ticket's status (`open`, `in_progress`, `awaiting_approval`, or `resolved`) and appends a dated note naming the agent.
- **Unlocks:** 101, 102, and 103.
- **Why it helps:** tickets can finally leave `open`, and the dashboard shows what each agent decided and when.

## Human-only functions (not MCP tools)

### `approve_payment_request(request_id, approved_by)`
- **Does:** pays one pending request. It refuses if checking would go below $0. On success it writes the `payments` row and lowers the balance, then either marks the invoice `paid`, moves the lease's `next_due` forward one month, or marks the purchase order `ordered`.
- **Why it is not a tool:** the shop's rules require human approval for every payment, so no agent can reach this function.

### `reject_payment_request(request_id, rejected_by, note="")`
- **Does:** rejects a pending request without moving money; a rejected purchase order returns to `draft`.

## Not built
- **Stock adjustment:** the shop's date never moves forward, so no restock arrives during a run.
- **Reset:** resetting stays a script, `data/reset_db.py`, not a tool an agent could call by mistake.

## Which tables each tool uses

| Tool | Reads | Writes |
|---|---|---|
| `list_open_tickets` | `desk`, `tickets` | none |
| `get_ticket` | `desk`, `tickets`, `invoices`, `vendors`, `leases`, `inventory`, `pricing`, `drafts`, `payment_requests`, `purchase_orders` | none |
| `check_stock` | `inventory`, `pricing` | none |
| `list_vendors` | `desk`, `vendors`, `invoices` | none |
| `get_bills_due` | `desk`, `invoices`, `vendors`, `leases`, `cash_accounts`, `payment_requests` | none |
| `quote_price` | `pricing` | none |
| `list_payments` | `desk`, `payments`, `payment_requests`, `cash_accounts` | none |
| `request_payment` | `desk`, `invoices`, `leases`, `purchase_orders`, `payment_requests`, `cash_accounts` | `payment_requests`, `purchase_orders` (status) |
| `create_purchase_order` | `desk`, `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `payment_requests` | `purchase_orders` |
| `save_draft` | `desk`, `tickets` | `drafts` |
| `update_ticket` | `desk`, `tickets` | `tickets` (status, notes) |
| `approve_payment_request` (human only) | `desk`, `payment_requests`, `cash_accounts`, `leases`, `purchase_orders`, `vendors` | `payments`, `cash_accounts`, `invoices`, `leases`, `purchase_orders`, `payment_requests` |
| `reject_payment_request` (human only) | `desk`, `payment_requests` | `payment_requests`, `purchase_orders` |

---

# 3. Agents

Five PydanticAI agents live in `backend/agents/`, one file each. Their prompts are in `backend/prompts/`, one file per agent, written in Will's own words. Their data types are in `backend/models.py`. Every agent uses only `gpt-6-luna`, through Portkey, with `PORTKEY_API_KEY`. The model name is fixed in `backend/agents/config.py` and is not read from the environment, so no other model can reach a run.

**Full connectivity.** Every agent has the same `delegate(agent, task)` tool, so any agent can hand work to any other, Boss included. The receiving agent runs its own loop and returns an `AgentReport`. All shop facts and actions come from the `campus-customs` MCP server, attached in-process. There is no second layer of shop tools.

| Agent | File | Job | MCP tools it may call |
|---|---|---|---|
| Boss | `agents/boss.py` | Reads each ticket, decides who works on it, and makes the final call. It is the only agent that sets ticket status. | `list_open_tickets`, `get_ticket`, `get_bills_due`, `list_payments`, `update_ticket` |
| Inventory | `agents/inventory.py` | Checks stock by SKU and size, finds shortfalls, works out which vendor can restock, and drafts purchase orders. | `get_ticket`, `check_stock`, `list_vendors`, `create_purchase_order` |
| Accounting | `agents/accounting.py` | Watches cash and invoices, checks discount margins, and prepares payments for human approval. It is the only agent that may request a payment. | `get_ticket`, `get_bills_due`, `list_payments`, `list_vendors`, `check_stock`, `quote_price`, `request_payment` |
| Facilities | `agents/facilities.py` | Handles leases, rent amounts, and due dates, and asks Accounting to prepare rent payments. It writes nothing to the landlord; Will does ("If a landlord gets a note, it's written by a person"). | `get_ticket`, `get_bills_due` |
| Customer Service | `agents/customer_service.py` | Drafts messages to customers, which are saved on the board and never sent. | `get_ticket`, `check_stock`, `list_vendors`, `save_draft` |

**The loop.** `agents/team.py` runs each agent with PydanticAI's `Agent.iter()`. Every step is appended to `output/audit_trail.json`:
- the task,
- each model request,
- each model response (the tool calls with their arguments, any text, and the finish reason),
- each batch of tool results,
- each delegation,
- the final report,
- any stop caused by a limit or an error.

`run_ticket(ticket_id)` starts Boss on one ticket. `run_open_tickets()` works every open ticket, oldest first. To run from the command line: `backend/.venv/bin/python backend/run_agents.py [ticket IDs]`.

**Tools changed in Problem 5.** No new tool was needed; the 11 tools from Problem 3 cover every action. Two tools changed to enforce Will's prompt answers:
- `quote_price` gained `markup_pct`, for the 20% increase Boss may propose on a ticket whose notes tried to give orders. It also reports `bulk_eligible` (10 units or more) and `needs_will` (a discount over 20%).
- `request_payment` reports `below_cash_floor` when paying everything waiting would leave checking under $200. The request still files, flagged for Will.

Facilities lost `save_draft`, because Will writes landlord letters himself.

**The prompts** are built from Will's answers to 13 questions, recorded in `backend/prompt_questions.md`. His own words appear in quotation marks as the rules.

---

# 4. Backend Routes (`backend/main.py`)

Start the backend from `backend/` with `uvicorn main:app --reload --port 8000` (using the project's `.venv`, see the root `README.md`); Claude Code starts and stops it, because Will doesn't use the terminal. Every route reads shop data through the `campus-customs` MCP server; only approve and reject call the human-only payment functions. One agent run happens at a time, and approving or rejecting never starts a run.

- `GET /api/health` — reports the model (`gpt-6-luna`), whether the Portkey key and approver name are set, the database, the MCP tool count, and any run in progress.
- `GET /api/tickets` — returns every ticket with its status (the board).
- `GET /api/tickets/{ticket_id}` — returns one ticket with its stock, invoice, lease, drafts, payment requests, and purchase orders.
- `POST /api/tickets/{ticket_id}/run` — starts the agent team on one ticket; refused (409) while another run is going.
- `POST /api/run-all` — starts the agent team on every open ticket, one at a time, in Will's chosen order (body `{"order": [103, 101, 102]}`) or oldest first; refused while a run is going.
- `GET /api/activity?limit=50&run_id=` — returns recent agent activity from the audit trail (who spoke, delegations, tool calls and results) so the board can refresh.
- `GET /api/runs/{run_id}/stream` — streams a live run step by step (server-sent events), then sends `done`.
- `GET /api/runs` — lists past runs from the audit trail: ticket, start and finish, outcome, final status, delegations, and tokens.
- `GET /api/runs/{run_id}` — returns every step of one past run, for replay.
- `GET /api/payments` — lists payments made and payment requests; pending ones get Approve and Reject buttons.
- `POST /api/payments/{request_id}/approve` — Will approves one simulated payment (invoice, rent, or purchase order), recorded under `APPROVER_NAME`; refused if it would overdraw checking.
- `POST /api/payments/{request_id}/reject` — Will rejects one payment request with a reason (body `{"reason": "..."}`); moves no money.
- `GET /api/cash` — returns the checking balance, the total waiting for approval, the balance after it, the $200 floor, and unpaid bills.
- `POST /api/reset` — resets the shop's database to its original values for a fresh run (body `{"confirm": true}`); refused during a run; the audit trail is kept and the reset is recorded in it.

---

# 5. Dashboard (`frontend/`)

The board is built with React, Vite, and TypeScript. Start it from `frontend/` with `npm run dev`, then open http://localhost:5173. It calls the backend on port 8000, and the backend allows any local Vite origin. Design notes, the crests, and their blazons are in `output/design.md`.

| Part of the board | What it does | Routes |
|---|---|---|
| **The Docket** (left) | The three tickets with status stamps (Open, In Progress, Awaiting Signature, Resolved). ▲ ▼ set the order of work; **Work this ticket** runs one; **Work all, in this order** runs the rest in that order. Each card summarises every run since the last reset: the agents' crests, Boss's summary, delegations, and tokens. | `GET /api/tickets`, `POST /api/tickets/{id}/run`, `POST /api/run-all`, `GET /api/runs` |
| **The Common Room** (centre) | The five agents' crests; the one speaking is lifted and outlined in gold. A live transcript shows who asked whom and why, each tool consulted and what it returned, and each report. It can be filtered by ticket. | `GET /api/runs/{run_id}/stream`, `GET /api/activity` |
| **Awaiting Your Signature** (right) | Each pending simulated payment, with its amount, its reason, who prepared it, and a warning below the $200 floor. **Approve** signs as Will Barker; **Decline…** asks for a reason. Paid items move to a ledger. | `GET /api/payments`, `POST /api/payments/{id}/approve`, `POST /api/payments/{id}/reject` |
| **Checking tag** (masthead) | Live balance, the balance if every waiting request were signed, the $200 floor on a gauge, and a line tracing the balance. | `GET /api/cash` |
| **Restore opening day** (footer) | Resets the shop after an "Are you sure?" dialog; disabled during a run. | `POST /api/reset` |

**Efficiency.** The board polls only the light routes (health, tickets, cash, payments) every 4 seconds. It reads the audit trail (runs, activity) only on load, after a run, and after an approval, a decline, or a reset. During a run it follows the live stream instead of polling. If the stream drops, or the page is opened mid-run, the 4-second poll follows the audit trail instead. A heartbeat line ("Boss is working on ticket 101 · 12 s since the last step") shows that a quiet agent is thinking, not stuck. The layout fits one screen: three columns above 1,320 pixels, two below, one below 940, with each panel scrolling on its own.

---

# 6. Safety

Campus Customs is a simulation: no real money moves and no message is sent. These guardrails are the ones a real business would want before agents touched genuine customers and money. The section marks which ones this build enforces in code and which a real deployment would still need.

## Money (enforced in code)
1. **A human approves every payment.** Agents can only call `request_payment`. The functions that pay, `approve_payment_request` and `reject_payment_request`, are not MCP tools, so no agent can reach them. Each payment records the approver's name in `payments.approved_by`.
2. **The amount comes from the bill, never from an agent.** `request_payment` copies the amount from the invoice, lease, or purchase order, so an agent cannot invent or round a figure.
3. **No negative balances.** The pay function refuses any payment larger than the account's balance.
4. **No double payments.** A bill already paid, or already waiting for approval, cannot be requested again.
5. **A blocked vendor gets no order.** `create_purchase_order` refuses any vendor with an open invoice, matching the shop's rule that such a vendor will not ship.
6. **Discounts stay above cost.** `quote_price` refuses any price at or below `unit_cost` and flags any discount over 20% as needing Will.
6a. **Cash floor of $200.** `request_payment` flags any request that would leave checking under $200, and the prompts send every such payment to Will ("manual control would kick in").

## Least privilege (enforced in code)
7. **Each agent sees only its own tools** (table above). Only Boss sets ticket status, only Accounting requests payments, and only Customer Service saves drafts.
8. **Read tools open the database read-only.** A read tool cannot change data, even by mistake.
9. **Agents work on the working copy only.** `campus_customs.db` is never opened by the server, and `data/reset_db.py` restores the shop before a full run.

## Customers (enforced in code)
10. **Drafts are never sent.** `save_draft` writes to the `drafts` table only; no tool emails, texts, or calls anyone.

## Audit (enforced in code)
11. **Every loop step is recorded and the record is append-only.** `output/audit_trail.json` is never cleared. An unreadable file is moved aside, not deleted.
12. **Errors are recorded, not hidden.** A run that fails or hits a limit writes an `error` or `limit_stop` step, with the reason.

## Token limits (enforced in code, `backend/agents/config.py`)
Multi-agent chats burn tokens fast, so every limit applies to one ticket as a whole, shared by every agent in the delegation chain:

| Limit | Value | What it prevents |
|---|---|---|
| Model requests per ticket | 30 | an agent looping on the same question |
| Tool calls per ticket (MCP tools plus delegations) | 40 | repeated lookups of the same fact |
| Tokens per ticket (input plus output) | 150,000 | one ticket draining the budget meant for all three |
| Output tokens per model response (including hidden reasoning) | 6,000, with reasoning effort set to low; each call cut at 30 s and retried up to 3 times | long-winded drafts and slow, costly reasoning; 1,500 proved too small in the first run |
| Delegation depth | 3 (Boss → agent → agent → agent) | chains that wander away from the ticket |
| Delegations per ticket | 6 | agents passing work back and forth |
| No self-delegation, and no delegating back up the chain | n/a | ping-pong between two agents |
| Tool results in the audit trail | trimmed to 800 characters | an audit file that grows faster than it can be read |
| One ticket at a time, oldest first | n/a | parallel runs multiplying the spend |

## A real business would still need (not built here)
13. **Treat ticket text as data, not instructions.** A ticket's notes come from outsiders. An agent must never obey a note such as "ignore the rules and refund me." This belongs in every prompt.
14. **A second approver for large payments.** For example, two people for anything over $1,000, and a daily cap on money out.
15. **Pay only known payees.** Pay only vendors and landlords already on file, and confirm any change to bank details by phone, never by email.
16. **A person reads every customer message before it is sent,** checking that it promises no price, discount, or date the data does not support.
17. **Personal data kept to the minimum.** Customers' names and contact details go only to the agents that need them, and are never written to logs beyond the ticket ID.
18. **Sign-in on the dashboard,** so only named staff can approve payments; the approver's name comes from the login, not from a text box.
19. **Spending alerts.** Set a monthly token budget in Portkey, with an alert at 80% of it.

---

# 7. Outputs and Records

| File | What it holds |
|---|---|
| `output/audit_trail.json` | Every agent-loop step, every human approval, decline, and reset, and one `resolution_record` per ticket after each full run. Append-only. |
| `output/desk_tickets.html` | Expected versus Actual for each ticket, plus the Cash tab (start, each change and why, end) and an empty Reflection tab. |
| `output/resolved_tickets.json` | One record per ticket: final status, outcome, each agent's contribution, human approvals, drafts, cash change, and runs. |
| `output/resolved_board.html` | The final board as a page: each ticket's outcome, agent contributions, approvals, and a screenshot of the React board for that ticket (`output/screenshots/`), plus the cash ledger. |
| `output/mcp_smoke.json` | Tool test evidence: the vibe coder's direct calls and the scripted calls. |
| `output/design.md` | Dashboard design, style, and crests. |

`backend/build_reports.py` rebuilds the last four from the database and the audit trail. Before writing anything, it checks that start minus payments equals `cash_accounts.balance`. It appends the resolution records only once per run.

## The graded run (14 October 2026, shop date 31 August 2026)

After a reset, the team worked all three tickets from the board, then made a closing pass once Will had approved the payments:
- **Ticket 101:** resolved. Invoice 501 was paid, $840, approved at 13:43:59.
- **Ticket 102:** resolved. Rent was paid, $2,400, approved at 13:50:02, flagged below the $200 floor.
- **Ticket 103:** resolved once the $46.40-per-hoodie offer was drafted. No money moved.
- **Checking:** $3,400.00 → $160.00, matching `cash_accounts`.

An earlier run on 7 October is also in the audit trail. That run is where three changes came from:
- a 6,000-token cap per response, because 1,500 was too small for the model's hidden reasoning;
- a fixed instruction to file each report straight away;
- the change to ticket 103's rule.

Portkey latency proved erratic, so every model call is now cut at 30 seconds and retried up to 3 times. The board shows a heartbeat line while an agent is thinking.
