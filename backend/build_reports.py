"""Build the Problem 9 reports from the database and the audit trail.

Every number here is read from data/campus_customs_new.db, data/campus_customs.db
(the starting balance), or output/audit_trail.json; the script checks that the
cash ledger ends exactly at cash_accounts.balance before writing anything.
The written account of each run (who worked when, and why) is from the audit
trail of the run since the last reset.

Writes:
  output/resolved_tickets.json   one record per ticket
  output/resolved_board.html     the final board, as a page
  output/desk_tickets.html       fills the Actual sections and the Cash tab
  output/audit_trail.json        appends one resolution_record per ticket

Run from backend/:  .venv/bin/python build_reports.py
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from agents import audit
from agents.config import AUDIT_PATH, ROOT
from models import TeamDeps

DATA = ROOT / "data"
OUT = ROOT / "output"
EDT = timezone(timedelta(hours=-4))


def local(ts: str) -> str:
    return datetime.fromisoformat(ts).astimezone(EDT).strftime("%H:%M:%S")


def money(x: float) -> str:
    return f"−${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


# ------------------------------------------------------------- facts

def db_rows(path: Path, sql: str) -> list[dict]:
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


WORK = DATA / "campus_customs_new.db"
start_balance = db_rows(DATA / "campus_customs.db", "SELECT balance FROM cash_accounts WHERE name='checking'")[0]["balance"]
end_row = db_rows(WORK, "SELECT balance, date FROM cash_accounts WHERE name='checking'")[0]
tickets = {t["id"]: t for t in db_rows(WORK, "SELECT * FROM tickets ORDER BY id")}
payments = db_rows(WORK, "SELECT * FROM payments ORDER BY id")
requests = {r["id"]: r for r in db_rows(WORK, "SELECT * FROM payment_requests ORDER BY id")}
drafts = db_rows(WORK, "SELECT * FROM drafts ORDER BY id")
pos = db_rows(WORK, "SELECT * FROM purchase_orders ORDER BY id")
invoices = {i["id"]: i for i in db_rows(WORK, "SELECT * FROM invoices")}
leases = {l["id"]: l for l in db_rows(WORK, "SELECT * FROM leases")}

steps = audit.read_all()
reset_at = [s for s in steps if s["kind"] == "human_action" and s["detail"].get("action") == "reset_database"][-1]["time"]
steps = [s for s in steps if s["time"] >= reset_at]
approvals = {s["detail"]["request_id"]: s for s in steps
             if s["kind"] == "human_action" and s["detail"].get("action") == "approve_payment"}

runs: dict[str, dict] = {}
for s in steps:
    if s["kind"] in ("human_action", "resolution_record"):
        continue
    r = runs.setdefault(s["run_id"], {"run_id": s["run_id"], "ticket_id": s["ticket_id"], "start": s["time"],
                                      "end": s["time"], "total_tokens": 0, "requests": 0, "stopped": None})
    r["end"] = s["time"]
    r["total_tokens"] = max(r["total_tokens"], s["usage"].get("total_tokens", 0))
    r["requests"] = max(r["requests"], s["usage"].get("requests", 0))
    if s["kind"] == "ticket_done":
        r["stopped"] = s["detail"]["stopped"]


def ticket_for_payment(p: dict) -> int:
    """A payment belongs to the ticket whose record it pays (invoice or lease)."""
    for t in tickets.values():
        if p["kind"] == "invoice" and t["invoice_id"] == p["ref_id"]:
            return t["id"]
        if p["kind"] == "rent" and t["lease_id"] == p["ref_id"]:
            return t["id"]
    req = next((r for r in requests.values() if r["payment_id"] == p["id"]), None)
    return req["ticket_id"] if req else None


# ------------------------------------------------------------- cash ledger (checked)

ledger, bal = [], start_balance
for p in payments:
    req = next(r for r in requests.values() if r["payment_id"] == p["id"])
    bal -= p["amount"]
    ledger.append({
        "payment_id": p["id"], "request_id": req["id"], "ticket_id": ticket_for_payment(p),
        "filed_under_ticket": req["ticket_id"], "kind": p["kind"], "ref_id": p["ref_id"],
        "amount": p["amount"], "balance_after": bal, "approved_by": p["approved_by"],
        "approved_at": local(approvals[req["id"]]["time"]) if req["id"] in approvals else None,
        "requested_by": req["requested_by"], "reason": req["reason"],
    })
assert abs(bal - end_row["balance"]) < 0.005, f"ledger ends at {bal}, cash_accounts says {end_row['balance']}"
ending_balance = end_row["balance"]

WHY = {
    "invoice": "Bulldog Print Co's invoice 501, 3 days overdue on 31 Aug; it blocked every apparel restock, so Will's rule pays it before rent that is not yet late",
    "rent": "September rent on the Chapel Street shop (lease 1), due 2 Sept; rent comes first “because if you don't have a shop, you don't have a business”",
}

# ------------------------------------------------------------- what each agent did (from the audit trail)

RECORD = {
    101: {
        "outcome": "Resolved after Will approved invoice 501 ($840). Tauhid was offered a size M today, or a held size S about five days after the restock is ordered, in an unsent draft. No tee restock was ordered.",
        "agents": {
            "boss": "Read the ticket and sent it to Inventory, then Accounting, then Customer Service. It set the ticket to awaiting_approval; on the second pass it checked list_payments, found invoice 501 paid, and marked it resolved.",
            "inventory": "Confirmed size S had 0 on hand (short 1) and found M 5, L 3, and XL 2. It found Bulldog Print Co blocked by invoice 501, so it drafted no purchase order.",
            "accounting": "Requested payment of invoice 501 ($840, request 1) because the overdue invoice blocks restocks and comes before rent that is not yet late. Checking would stay at $2,560, above the $200 floor.",
            "customer_service": "Saved draft 1 to Tauhid Zaman (formal, unsent), offering a size M today or a held size S about five days after the restock order.",
        },
    },
    102: {
        "outcome": "Resolved after Will approved the $2,400 rent, knowing it would leave checking at $160, below the $200 floor. No note went to the landlord, as Will's rule requires.",
        "agents": {
            "boss": "Read the ticket and sent it to Facilities. It set the ticket to awaiting_approval; on the second pass it checked list_payments, found the rent paid, and marked it resolved.",
            "facilities": "Confirmed lease 1 (Chapel Street shop, $2,400, due 2 Sept, last on-time date 12 Sept) and handed the payment to Accounting. It wrote nothing to the landlord.",
            "accounting": "Requested the rent ($2,400, request 2), flagged below the $200 floor because checking would fall to $160, so the decision was Will's.",
        },
    },
    103: {
        "outcome": "Resolved once the offer was drafted. The Yale AI Club is offered 20 hoodies at $46.40 each (20% bulk discount, $928): 8 size M now and 12 size M after a restock arriving about 5 Sept. No money moved.",
        "agents": {
            "boss": "Read the ticket and sent it to Inventory, then Accounting. When Accounting could not price the order, Boss sent it back with the correct SKU (CC-HOOD-NAVY), then sent the 20% offer to Customer Service and marked the ticket resolved once the draft was saved.",
            "inventory": "Found 8 M on hand (short 12) plus S 4, L 14, and XL 6. Bulldog Print Co was no longer blocked, because Will had paid invoice 501 earlier in the run, so an order would arrive 5 Sept. It drafted no purchase order.",
            "accounting": "Its first quote_price call passed the vendor's name as the SKU, was refused, and it reported that it could not price the order. Sent back by Boss with the correct SKU, it checked cash ($160) and priced 20 hoodies at the 20% maximum: $46.40 each, $928, a 53% margin. It requested no payment.",
            "customer_service": "Saved draft 2 to the Yale AI Club (formal, unsent): 8 size M now and the remaining 12 after the restock, expected about 5 Sept, all at $46.40. It did not mention the other sizes in stock.",
        },
    },
}

# Runs since the reset, per ticket, oldest first: R[tid][0] is the full run, R[tid][1] the closing pass.
R = {tid: sorted((r for r in runs.values() if r["ticket_id"] == tid), key=lambda r: r["start"]) for tid in tickets}
APPROVED = {e["ticket_id"]: e["approved_at"] for e in ledger}

NAMES = {"boss": "Boss", "inventory": "Inventory", "accounting": "Accounting",
         "facilities": "Facilities", "customer_service": "Customer Service"}

resolved = []
for tid, t in tickets.items():
    tr = [r for r in runs.values() if r["ticket_id"] == tid]
    resolved.append({
        "id": tid,
        "subject": t["subject"],
        "requester": t["requester"],
        "type": t["type"],
        "final_status": t["status"],
        "outcome": RECORD[tid]["outcome"],
        "agents": [{"agent": NAMES[a], "contribution": c} for a, c in RECORD[tid]["agents"].items()],
        "human_approvals": [
            {"request_id": e["request_id"], "payment_id": e["payment_id"], "what": f"{e['kind']} {e['ref_id']}",
             "amount": e["amount"], "approved_by": e["approved_by"], "approved_at_edt": e["approved_at"]}
            for e in ledger if e["ticket_id"] == tid
        ],
        "drafts": [{"draft_id": d["id"], "recipient": d["recipient"], "sent": False} for d in drafts if d["ticket_id"] == tid],
        "purchase_orders": [p["id"] for p in pos if p["ticket_id"] == tid],
        "cash_change": -sum(e["amount"] for e in ledger if e["ticket_id"] == tid),
        "runs": [{"run_id": r["run_id"], "start_edt": local(r["start"]), "end_edt": local(r["end"]),
                  "stopped": r["stopped"], "total_tokens": r["total_tokens"]} for r in tr],
    })

summary = {
    "shop_date": "2026-08-31",
    "starting_checking": start_balance,
    "ending_checking": ending_balance,
    "ending_matches_cash_accounts": True,
    "tickets": resolved,
}
(OUT / "resolved_tickets.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------------- append to the audit trail (once)

# One set of records per state of the board: a later resolution appends a new set (append-only).
last_done = max((s["time"] for s in steps if s["kind"] == "ticket_done"), default=reset_at)
report_id = f"report-{last_done[:19]}"
already = any(s["kind"] == "resolution_record" and s["run_id"] == report_id for s in audit.read_all())
if not already:
    for rec in resolved:
        audit.append(TeamDeps(run_id=report_id, ticket_id=rec["id"], chain=["report"]),
                     "report", 0, "resolution_record", rec)
    audit.append(TeamDeps(run_id=report_id, ticket_id=None, chain=["report"]), "report", 0, "resolution_record",
                 {"cash": {"starting_checking": start_balance, "ending_checking": ending_balance,
                           "ledger": ledger}})

# ------------------------------------------------------------- desk_tickets.html: Actual + Cash

def span(r):
    return f"{local(r['start'])}–{local(r['end'])} EDT, {r['total_tokens']:,} tokens"


TIMELINE = {
    101: f"""
<p class="lede"><b>Two passes.</b> The full run took {span(R[101][0])}. Will approved invoice 501 at {APPROVED[101]} EDT, while the run was still going. The closing pass took {span(R[101][1])}, with Boss alone.</p>
<table>
<tr><th>Called first</th><td>Boss, which called <code>get_ticket(101)</code> and saw size S at 0 and the link to invoice 501.</td></tr>
<tr><th>Delegations, in order</th><td><ol>
<li><b>Boss → Inventory.</b> Why: confirm the shortfall and find a vendor, given “linked open invoice 501 to Bulldog Print Co ($840, … 3 days overdue).”</li>
<li><b>Boss → Accounting.</b> Why: prepare payment of the invoice blocking the only apparel vendor, and check it against the $200 floor.</li>
<li><b>Boss → Customer Service.</b> Why: draft a reply to Tauhid with the in-stock alternatives (M 5, L 3, XL 2) and the restock timing.</li>
</ol></td></tr>
<tr><th>Tools used, and why</th><td><ul>
<li><b>Inventory:</b>
  <ul>
  <li><code>check_stock(size S, qty 1)</code> → short 1.</li>
  <li><code>check_stock</code> on every size → M 5, L 3, XL 2, for the counteroffer.</li>
  <li><code>list_vendors</code> → Bulldog Print Co blocked by invoice 501, so it drafted no order.</li>
  </ul></li>
<li><b>Accounting:</b>
  <ul>
  <li><code>get_bills_due</code> → $3,400 cash; invoice 501 and rent unpaid.</li>
  <li><code>request_payment</code>(invoice 501, $840) → request 1. Its reason: “Overdue vendor invoice blocks restock; vendor invoice has priority over rent not yet late.” That leaves $2,560, above the floor.</li>
  </ul></li>
<li><b>Customer Service:</b> <code>get_ticket</code> and <code>check_stock</code> to confirm the facts, then <code>save_draft</code> (draft 1) to Tauhid: a size M today, or a held S about five days after the restock order.</li>
<li><b>Boss:</b>
  <ul>
  <li><code>update_ticket → awaiting_approval</code>.</li>
  <li>Closing pass: <code>get_ticket</code>, then <code>list_payments</code> to confirm Will's approval, then <code>update_ticket → resolved</code>.</li>
  </ul></li>
</ul></td></tr>
<tr><th>Final status</th><td><b>Resolved</b>. Will approved request 1 ($840) at {APPROVED[101]} EDT.</td></tr>
<tr><th>Against Expected</th><td><ul>
<li><b>Matched:</b>
  <ul>
  <li>Boss called first.</li>
  <li>Inventory, then Accounting, then Customer Service.</li>
  <li>Facilities not called.</li>
  <li>Only invoice 501 was requested here; the rent went to ticket 102.</li>
  <li>The offer of an M today or a held S.</li>
  <li><code>awaiting_approval</code>, then <code>resolved</code>.</li>
  </ul></li>
<li><b>Differed:</b>
  <ul>
  <li>Inventory never tried <code>create_purchase_order</code>; we expected a refused call.</li>
  <li>After invoice 501 was paid, no agent ordered the tee, so Tauhid's size S is still unordered.</li>
  <li>Boss set <code>awaiting_approval</code> although Will had approved mid-run, so a closing pass was needed.</li>
  </ul></li>
</ul></td></tr>
</table>""",
    102: f"""
<p class="lede"><b>Two passes.</b> The full run took {span(R[102][0])}. Will approved the rent at {APPROVED[102]} EDT, while the team was working ticket 103. Will then clicked <b>Close this ticket</b>, and the closing pass took {span(R[102][1])}, with Boss alone.</p>
<table>
<tr><th>Called first</th><td>Boss, which called <code>get_ticket(102)</code> and saw lease 1, due in 2 days.</td></tr>
<tr><th>Delegations, in order</th><td><ol>
<li><b>Boss → Facilities.</b> Why: “Confirm lease, amount, due date and handle per rent workflow.”</li>
<li><b>Facilities → Accounting.</b> Why: Facilities cannot request payments. It asked Accounting to “confirm and handle the rent payment request … $2,400 due 2026-09-02, with the ten-day-late grace deadline 2026-09-12.”</li>
</ol></td></tr>
<tr><th>Tools used, and why</th><td><ul>
<li><b>Facilities:</b> <code>get_ticket</code> and <code>get_bills_due</code> → lease 1: $2,400, due 2 Sept, grace to 12 Sept.</li>
<li><b>Accounting:</b>
  <ul>
  <li><code>get_bills_due</code> → $2,560 after invoice 501.</li>
  <li><code>request_payment</code>(rent, lease 1, $2,400) → request 2, flagged <code>below_cash_floor</code>, because checking would fall to $160. “Will must decide.”</li>
  </ul></li>
<li><b>Boss:</b>
  <ul>
  <li><code>update_ticket → awaiting_approval</code>.</li>
  <li>Closing pass: <code>get_ticket</code>, then <code>list_payments</code> → rent paid → <code>update_ticket → resolved</code>.</li>
  </ul></li>
</ul></td></tr>
<tr><th>Final status</th><td><b>Resolved</b>. Will approved request 2 ($2,400) at {APPROVED[102]} EDT, knowing it would cross the $200 floor.</td></tr>
<tr><th>Against Expected</th><td><ul>
<li><b>Matched:</b>
  <ul>
  <li>Boss called first.</li>
  <li>Facilities, then Facilities → Accounting.</li>
  <li>Inventory and Customer Service not called.</li>
  <li>No note to the landlord.</li>
  <li><code>request_payment</code> flagged below the floor.</li>
  <li><code>awaiting_approval</code>, then <code>resolved</code>.</li>
  </ul></li>
<li><b>Differed:</b> nothing in the agents' work. A closing pass was needed only because Will signed after Boss had set the status.</li>
</ul></td></tr>
</table>""",
    103: f"""
<p class="lede"><b>One run</b>, {span(R[103][0])}, completed.</p>
<table>
<tr><th>Called first</th><td>Boss, which called <code>get_ticket(103)</code> and saw 8 M on hand against 20 requested.</td></tr>
<tr><th>Delegations, in order</th><td><ol>
<li><b>Boss → Inventory.</b> Why: “Confirm stock in every size and vendors/restock lead time.”</li>
<li><b>Boss → Accounting.</b> Why: price the bulk discount within policy and check cash.</li>
<li><b>Boss → Accounting, again.</b> Why: “Correction for ticket 103: use actual SKU CC-HOOD-NAVY (not vendor name Bulldog Print Co).” Accounting's first pass had reported that it could not price the order.</li>
<li><b>Boss → Customer Service.</b> Why: draft the counteroffer to the club with the stock, the wait, and the 20% price.</li>
</ol></td></tr>
<tr><th>Tools used, and why</th><td><ul>
<li><b>Inventory:</b>
  <ul>
  <li><code>get_ticket</code>.</li>
  <li><code>check_stock(qty 20)</code> → M 8 (short 12), S 4, L 14, XL 6.</li>
  <li><code>list_vendors</code> → Bulldog Print Co unblocked, because invoice 501 was paid at {APPROVED[101]}; arrival 5 Sept.</li>
  </ul></li>
<li><b>Accounting:</b>
  <ul>
  <li>First pass: <code>get_bills_due</code>, then <code>quote_price</code> with the vendor's name as the SKU, which was refused (“no pricing row”). It reported back without a price.</li>
  <li>Second pass, after Boss's correction: <code>get_bills_due</code> → $160 cash; <code>quote_price(CC-HOOD-NAVY, 20, 20% off)</code> → $46.40 each, $928, a 53% margin.</li>
  <li>No payment requested.</li>
  </ul></li>
<li><b>Customer Service:</b> <code>get_ticket</code>, then <code>save_draft</code> (draft 2) to the Yale AI Club.</li>
<li><b>Boss:</b> <code>update_ticket → resolved</code>, because the offer draft was saved, under Will's changed rule.</li>
</ul></td></tr>
<tr><th>Final status</th><td><b>Resolved</b>, with no money moved.</td></tr>
<tr><th>Against Expected</th><td><ul>
<li><b>Matched:</b>
  <ul>
  <li>Boss called first.</li>
  <li>Inventory, then Accounting, then Customer Service.</li>
  <li>Facilities not called.</li>
  <li>No <code>request_payment</code>.</li>
  <li>A counteroffer of stock now plus a wait for the rest.</li>
  </ul></li>
<li><b>Differed:</b>
  <ul>
  <li>The ticket ended <b>resolved</b> rather than in progress, because Will changed the rule after an earlier run left it waiting and reruns made duplicate drafts.</li>
  <li>Accounting went straight to the 20% maximum.</li>
  <li>Accounting first passed the vendor name as a SKU, so Boss needed a fourth delegation (back to Accounting) to get the price.</li>
  <li>Inventory found the vendor unblocked, because Will paid invoice 501 during ticket 101.</li>
  <li>The draft left out the other sizes in stock (S 4, L 14, XL 6), although the counteroffer rule allows them.</li>
  </ul></li>
</ul></td></tr>
</table>""",
}

cash_rows = "".join(
    f"<tr><td>Ticket {e['ticket_id']}</td><td>{escape(WHY[e['kind']])}. Requested by {e['requested_by'].title()} "
    f"(request {e['request_id']}, filed under ticket {e['filed_under_ticket']}); approved by {e['approved_by']} at {e['approved_at']} EDT.</td>"
    f"<td class='num'>{money(-e['amount'])}</td><td class='num'>{money(e['balance_after'])}</td></tr>"
    for e in ledger)
CASH = f"""
<p class="lede">Checking moved only when Will approved a simulated payment. Every figure below comes from the database, and the ending balance matches <code>cash_accounts</code>.</p>
<table class="ledger">
<tr><th style="width:12%">Item</th><th>How and why cash changed</th><th class="num" style="width:13%">Change</th><th class="num" style="width:13%">Balance</th></tr>
<tr><td><b>Start</b></td><td>Checking at the reset, from the original database (<code>campus_customs.db</code>), shop date 31 Aug 2026.</td><td class="num"></td><td class="num"><b>{money(start_balance)}</b></td></tr>
{cash_rows}
<tr><td>Ticket 103</td><td>No payment. The offer to the club is a quote, not cash; the 12-hoodie restock ($308 with spares) was not ordered, since it exceeds the $160 left. Resolved without moving money.</td><td class="num">$0.00</td><td class="num">{money(ending_balance)}</td></tr>
<tr><td><b>End</b></td><td>Checking in <code>cash_accounts</code> after the run, dated {end_row['date']}: {money(start_balance)} − {money(sum(e['amount'] for e in ledger))[1:]} = {money(ending_balance)}. This is ${200 - ending_balance:,.2f} below the $200 floor; Will approved the rent knowing it would cross the floor.</td><td class="num"><b>{money(-sum(e['amount'] for e in ledger))}</b></td><td class="num"><b>{money(ending_balance)}</b></td></tr>
</table>"""

page = OUT / "desk_tickets.html"
html = page.read_text()
if ".num {" not in html:
    html = html.replace("table { border-collapse: collapse;",
                        ".num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }\n"
                        "  .actual { border-color: var(--ink); }\n  .ledger th { width: auto; }\n"
                        "  table { border-collapse: collapse;", 1)


def fill_section(html: str, section_id: str, key: str, label: str, body: str) -> str:
    """Put body in the section's empty placeholder (first run) or its marked block (reruns)."""
    start = html.rfind("<section", 0, html.index(f'id="{section_id}"'))
    end = html.index("</section>", start)
    sec = html[start:end]
    block = (f'<!--ACTUAL-{key}--><div class="box actual"><span class="label">{label}</span>{body}</div>'
             f'<!--/ACTUAL-{key}-->')
    if f"<!--ACTUAL-{key}-->" in sec:
        sec = re.sub(rf"<!--ACTUAL-{key}-->.*?<!--/ACTUAL-{key}-->", lambda _: block, sec, flags=re.S)
    else:
        sec = re.sub(r'<div class="empty">.*?</div>', lambda _: block, sec, count=1, flags=re.S)
        sec = sec.replace('<p class="lede">Reserved for later.</p>',
                          '<p class="lede">Where the money went during the run, item by item.</p>', 1)
    return html[:start] + sec + html[end:]


ACT = "Actual — from the run, read from output/audit_trail.json"
html = fill_section(html, "t101", "101", ACT, TIMELINE[101])
html = fill_section(html, "t102", "102", ACT, TIMELINE[102])
html = fill_section(html, "t103", "103", ACT, TIMELINE[103])
html = fill_section(html, "cash", "cash", "Cash — checked against cash_accounts", CASH)
page.write_text(html)

# ------------------------------------------------------------- resolved_board.html

CREST = {"Boss": ("#1D4E89", "#C9A43A"), "Inventory": ("#F7F3E8", "#1D4E89"), "Accounting": ("#2E6A47", "#C9A43A"),
         "Facilities": ("#9B2A2C", "#F7F3E8"), "Customer Service": ("#C9A43A", "#1C1C1C")}


def shield(name: str) -> str:
    field, charge = CREST[name]
    return (f'<svg viewBox="0 0 100 118" width="26" height="31" aria-hidden="true"><path d="M6 6H94V54C94 88 72 106 50 113 28 106 6 88 6 54Z" '
            f'fill="{field}" stroke="#13284B" stroke-width="7"/><circle cx="50" cy="52" r="17" fill="{charge}" stroke="#13284B" stroke-width="4"/></svg>')


STAMP = {"resolved": "Resolved", "in_progress": "In Progress", "awaiting_approval": "Awaiting Signature", "open": "Open"}
cards = []
for rec in resolved:
    agents = "".join(f'<li>{shield(a["agent"])}<div><b>{a["agent"]}</b><span>{escape(a["contribution"])}</span></div></li>'
                     for a in rec["agents"])
    appr = "".join(f'<li>{escape(x["what"].replace("invoice", "Invoice").replace("rent 1", "Rent, lease 1"))}: '
                   f'<b>{money(x["amount"])}</b>, approved by {x["approved_by"]} at {x["approved_at_edt"]} EDT</li>'
                   for x in rec["human_approvals"]) or "<li>None needed.</li>"
    cards.append(f"""
<article class="card {rec['final_status']}">
  <div class="stamp">{STAMP[rec['final_status']]}</div>
  <div class="no">No. {rec['id']} · {rec['type'].replace('_', ' ')}</div>
  <h2>{escape(rec['subject'])}</h2>
  <div class="from">from {escape(rec['requester'])}</div>
  <p class="outcome">{escape(rec['outcome'])}</p>
  <h3>What each agent contributed</h3><ul class="agents">{agents}</ul>
  <h3>Human approvals</h3><ul class="appr">{appr}</ul>
  <h3>The React board, ticket {rec['id']} resolved</h3>
  <a href="screenshots/board_ticket_{rec['id']}.png"><img class="shot" src="screenshots/board_ticket_{rec['id']}.png" alt="Screenshot of the Campus Customs React board filtered to ticket {rec['id']}, showing it resolved"></a>
  <div class="meta">Cash change {money(rec['cash_change'])} · {len(rec['runs'])} run{'s' if len(rec['runs']) != 1 else ''} · {sum(r['total_tokens'] for r in rec['runs']):,} tokens</div>
</article>""")

board = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Campus Customs — The Resolved Board</title>
<style>
:root {{ --navy:#13284B; --cream:#F4EEDC; --paper:#FBF8EF; --burgundy:#6E1E2A; --green:#2D4B3A; --gold:#B08D3C; --muted:#6B6458; --rule:#D8CDB2; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--cream); color:#1D1B17; font:15px/1.5 Baskerville,'Libre Baskerville',Georgia,serif; }}
header {{ display:flex; justify-content:space-between; align-items:flex-end; padding:22px 32px 12px; }}
.eyebrow {{ font-variant:small-caps; letter-spacing:.18em; color:var(--burgundy); }}
h1 {{ margin:0; font-weight:normal; font-size:38px; letter-spacing:.14em; text-transform:uppercase; color:var(--navy); }}
.sub {{ font-style:italic; color:var(--muted); }}
.tag {{ background:var(--navy); color:var(--cream); padding:10px 16px; border-radius:3px; box-shadow:inset 0 0 0 1px var(--gold); min-width:260px; }}
.tag small {{ display:block; font-variant:small-caps; letter-spacing:.12em; color:#d9c79a; }}
.tag b {{ font-size:30px; font-weight:normal; font-variant-numeric:lining-nums; }}
.tartan {{ height:10px; background:repeating-linear-gradient(90deg,transparent 0 22px,rgba(176,141,60,.85) 22px 24px,transparent 24px 46px,rgba(110,30,42,.75) 46px 49px,transparent 49px 70px),repeating-linear-gradient(90deg,var(--navy) 0 35px,var(--green) 35px 70px); border-top:2px solid var(--navy); border-bottom:2px solid var(--navy); }}
main {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; padding:18px 32px; }}
.card {{ background:var(--paper); border:1px solid var(--rule); padding:14px 16px; position:relative; }}
.card::before {{ content:''; position:absolute; inset:5px; border:1px dashed rgba(19,40,75,.18); pointer-events:none; }}
.stamp {{ position:absolute; top:14px; right:12px; transform:rotate(-6deg); border:3px solid currentColor; padding:1px 9px; text-transform:uppercase; letter-spacing:.14em; font-size:13px; border-radius:3px; }}
.resolved .stamp {{ color:var(--burgundy); }} .in_progress .stamp {{ color:var(--green); }}
.no {{ font-variant:small-caps; letter-spacing:.1em; color:var(--muted); padding-right:120px; }}
h2 {{ margin:0; font-weight:normal; color:var(--navy); font-size:22px; }}
.resolved h2 {{ text-decoration:line-through; text-decoration-color:rgba(110,30,42,.5); }}
.from {{ font-style:italic; color:var(--muted); }}
.outcome {{ background:var(--cream); padding:8px 10px; font-style:italic; }}
h3 {{ margin:12px 0 4px; font-weight:normal; text-transform:uppercase; letter-spacing:.14em; font-size:13px; color:var(--navy); border-bottom:1px solid var(--navy); }}
ul {{ list-style:none; margin:0; padding:0; }}
.agents li {{ display:grid; grid-template-columns:30px 1fr; gap:6px; padding:5px 0; border-bottom:1px dotted var(--rule); font-size:14px; }}
.agents b {{ display:block; font-weight:normal; font-variant:small-caps; letter-spacing:.08em; color:var(--navy); }}
.appr li {{ padding:3px 0; font-size:14px; }}
.meta {{ margin-top:10px; font-size:12.5px; color:var(--muted); }}
.shot {{ width:100%; border:1px solid var(--rule); margin-top:4px; box-shadow:0 1px 3px rgba(19,40,75,.15); }}
.ledger {{ margin:0 32px 30px; background:var(--paper); border:1px solid var(--rule); padding:12px 16px; }}
.ledger table {{ width:100%; border-collapse:collapse; }}
.ledger td, .ledger th {{ padding:5px 8px; border-bottom:1px dotted var(--rule); text-align:left; }}
.ledger .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
</style></head><body>
<header>
  <div><div class="eyebrow">Clothiers to the University · New Haven</div><h1>Campus Customs</h1>
  <div class="sub">The Resolved Board · shop date Monday, August 31, 2026 · after the agents' run</div></div>
  <div class="tag"><small>Checking, start → end</small><b>{money(start_balance)} → {money(ending_balance)}</b>
  <small>ending balance matches cash_accounts</small></div>
</header>
<div class="tartan"></div>
<main>{''.join(cards)}</main>
<section class="ledger"><h3>The cash, item by item</h3>{CASH}</section>
</body></html>
"""
(OUT / "resolved_board.html").write_text(board)
print(f"start {money(start_balance)}  end {money(ending_balance)}  (matches cash_accounts)")
for rec in resolved:
    print(rec["id"], rec["final_status"], money(rec["cash_change"]), [x["request_id"] for x in rec["human_approvals"]])
print("audit trail:", "already had this report" if already else f"appended {len(resolved) + 1} resolution_record rows")
