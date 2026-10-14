# Design: The Agents' Board

`frontend/` is the dashboard for Campus Customs, built with React, Vite, and TypeScript. It calls the Problem 7 routes in `backend/main.py` on port 8000. Start it from `frontend/` with `npm run dev`, then open http://localhost:5173. The backend allows any local Vite origin (`localhost` or `127.0.0.1`, any port), so the browser can call it directly.

## The brief, and where each part lives

| Will asked for | Where it is on the board | Route it calls |
|---|---|---|
| The three tickets | **The Docket** (left): one card per ticket with its number, type, subject, and requester | `GET /api/tickets` |
| Choose which ticket is worked first | ▲ ▼ arrows reorder the docket (First, Second, Third). **Work this ticket** runs one ticket; **Work all, in this order** runs them in the chosen order | `POST /api/tickets/{id}/run`, `POST /api/run-all` with `{"order": [...]}` |
| Show the agents working and talking | **The Common Room** (centre): five crests, with the one speaking now lifted and outlined in gold. Below, a live transcript: who asked whom, what each agent said, every tool consulted, and what came back | `GET /api/runs/{run_id}/stream` (live), `GET /api/activity` (record) |
| Mark each ticket's resolution | A rubber stamp on each card: Open, In Progress, Awaiting Signature, or **Resolved** (burgundy, with the subject struck through) | `GET /api/tickets` (polled every 3 seconds) |
| A visible summary of agent activity per ticket | On each card: the crests of the agents who worked the last run, Boss's one-line summary, the number of delegations, tokens used, and the outcome. The transcript can be filtered to one ticket | `GET /api/runs` |
| Human approval when asked | **Awaiting Your Signature** (right): each pending simulated payment, with its amount, why it was requested, who prepared it, and a warning when it would cross the $200 floor. **Approve** signs it as Will Barker; **Decline…** asks for a reason. Paid items move to the ledger below | `GET /api/payments`, `POST /api/payments/{id}/approve`, `POST /api/payments/{id}/reject` |
| A live checking-balance tracker | The navy tag in the masthead: the balance (it counts up or down when it changes), a gauge showing the balance, the balance if every waiting request were signed, and the $200 floor; a small line traces the balance through the session | `GET /api/cash` (polled every 3 seconds) |
| Reset for a fresh run | **Restore opening day** in the footer, behind an "Are you sure?" dialog; disabled during a run | `POST /api/reset` |

Approving or declining never starts a run, and the Work buttons are disabled while a run is going, as Will's Problem 7 answers require.

## Style: J. Press, New Haven, about 1960

J. Press dressed Yale men from its York Street shop, and its look then was quiet, Ivy, and exact. The board borrows that manner:

- **Colour:** J. Press navy `#13284B` for ink and the masthead tag; Yale blue `#00356B`; cream `#F4EEDC` and paper `#FBF8EF` for grounds; club green `#2D4B3A`; burgundy `#6E1E2A` for stamps and warnings; old gold `#B08D3C`, used sparingly.
- **Type:** Baskerville throughout (falling back to Libre Baskerville, Big Caslon, then Georgia). Headings are spaced capitals, labels are small capitals, and figures are old-style in text and lining in the money columns.
- **Details:**
  - a navy-and-green tartan band under the masthead, with gold and burgundy overchecks;
  - ticket cards with a dashed inner line, like a stitched garment label;
  - status shown as a tilted rubber stamp;
  - the balance on a navy hang-tag with a gold keyline.
- **Restraint:** no gradients except the tartan, no shadows heavier than a hairline, and motion only where it carries meaning (the speaking crest, the changing balance).

## The crests

Each agent bears a shield drawn in code (SVG) in `frontend/src/components/Crest.tsx`. The arms follow the basic rules of heraldry:
- **The rule of tincture:** a metal (Or, gold; Argent, silver) is never laid on a metal, nor a colour (Azure, Gules, Vert, Sable) on a colour.
- **A heater shield,** with one simple charge chosen to fit each agent's job.
- **A motto scroll beneath.**

They are drawn as a 1960s graphic designer would draw them: flat colour, a heavy navy outline, a thin gold inner line, and no shading. That follows the Yale shield, an open book on blue, which also serves as Will's own mark in the masthead.

| Agent | Blazon | Why | Motto |
|---|---|---|---|
| Boss | *Azure, a crown Or* (gold on blue) | the one who makes the final call | Primus inter pares, "first among equals" |
| Inventory | *Argent, a chevron Azure between three lozenges Gules* (blue and red on silver) | the chevron as a stockroom roof; the lozenges as bales of goods | Omnia numerata, "everything counted" |
| Accounting | *Vert, three bezants* (gold on green) | in heraldry a bezant is a gold coin | Ratio vincit, "reckoning wins" |
| Facilities | *Gules, a tower Argent* (silver on red) | the shop's building | Domus nostra, "our house" |
| Customer Service | *Or, a quill in bend Sable* (black on gold) | the pen that writes every draft | Verba cum cura, "words with care" |
| Will (the proprietor) | *Azure, an open book Argent* (after Yale) | the human who signs | Manu propria, "by his own hand" |

## How it is built

- `src/api.ts`: one typed function per backend route; the base URL comes from `VITE_API_BASE` (default `http://127.0.0.1:8000`).
- `src/types.ts`: the shapes the routes return.
- `src/describe.ts`: turns each audit-trail step into a plain sentence for the Common Room. Examples: "Boss asks Inventory: …", "consults check_stock(sku=…)", and "check_stock → …".
- `src/components/`: `Docket`, `CommonRoom`, `Approvals`, `CashTracker`, `Crest`.
- `src/App.tsx`: polls health, tickets, cash, and payments every 4 seconds. It reads runs and activity only on load, after a run, and after an action. During a run it follows the live stream, falls back to polling if the stream drops, and shows a heartbeat so a long model call never looks frozen.

The layout uses three columns on a wide screen. It drops to two columns below 1,320 pixels, with approvals under the docket, and to one column below 940 pixels, with approvals first.
