"""Campus Customs MCP server — the shop tools every agent calls.

Every tool reads or writes ../data/campus_customs_new.db, the working copy
(set CC_DB_PATH to point at another copy, as the smoke test does). The original
data/campus_customs.db is never opened here; run data/reset_db.py to reset.
Tools return only what the database holds, plus dates and sums worked out from it.

Money rule: agents can only *request* a payment. approve_payment_request() and
reject_payment_request() at the bottom of this file are plain functions, not
MCP tools, so no agent can call them; the dashboard's approval step calls them
with the human's name.

Run from the project root (stdio):  .venv/bin/python mcp_server/server.py
Run (HTTP):                         .venv/bin/python mcp_server/server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import calendar
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = Path(os.environ.get("CC_DB_PATH", ROOT / "data" / "campus_customs_new.db"))
SCHEMA = ROOT / "data" / "schema_additions.sql"

TICKET_STATUSES = ("open", "in_progress", "awaiting_approval", "resolved")
CASH_FLOOR = 200.0          # Will's rule: below $200, manual control
BULK_MIN_QTY = 10           # Will's rule: bulk starts at 10 units
AGENT_MAX_DISCOUNT_PCT = 20 # Will's rule: larger discounts need Will

mcp = FastMCP("campus-customs")


# ---------------------------------------------------------------- helpers

def _read() -> sqlite3.Connection:
    """Open the working copy read-only, so a read tool can never change it."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _write() -> sqlite3.Connection:
    """Open the working copy for writing; refuse to create a new, empty file."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} is missing; run data/reset_db.py.")
    conn = sqlite3.connect(DB_PATH, isolation_level="IMMEDIATE")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_tables() -> None:
    with _write() as conn:
        conn.executescript(SCHEMA.read_text())


def _today(conn: sqlite3.Connection) -> str:
    """The shop's "today" comes from desk.date_today, never the real clock."""
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _add_days(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def _add_month(day: str) -> str:
    d = date.fromisoformat(day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month,
                     day=min(d.day, calendar.monthrange(year, month)[1])).isoformat()


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _cash(conn: sqlite3.Connection, account: str = "checking") -> float | None:
    row = conn.execute(
        "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
    ).fetchone()
    return row["balance"] if row else None


def _pending_total(conn: sqlite3.Connection) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE status = 'pending_approval'"
    ).fetchone()[0]


def _refuse(reason: str, **extra) -> dict:
    return {"ok": False, "refused": reason, **extra}


# ------------------------------------------------------------- read tools

@mcp.tool
def list_open_tickets(status: str = "open") -> dict:
    """List the tickets on the board with a given status (default "open"),
    oldest first, with the shop's date_today.

    Boss calls this first to see every request and decide which agent takes it.
    Each ticket carries its links: sku/size/qty for product requests,
    lease_id for rent, invoice_id for a vendor bill.
    Statuses: open, in_progress, awaiting_approval, resolved.
    """
    with _read() as conn:
        today = _today(conn)
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            WHERE status = ?
            ORDER BY created_at, id
            """,
            (status,),
        ).fetchall()
    return {
        "date_today": today,
        "status": status,
        "count": len(rows),
        "tickets": [dict(r) for r in rows],
    }


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket with every record it links to: its invoice and that
    invoice's vendor, its lease, the inventory and pricing rows for its SKU
    and size, and any drafts, payment requests, and purchase orders filed
    against it.

    Any agent handed a ticket calls this first to see the whole situation in
    one call.
    """
    with _read() as conn:
        today = _today(conn)
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return _refuse(f"No ticket {ticket_id}.")
        out: dict = {"date_today": today, "ticket": dict(t)}
        if t["invoice_id"] is not None:
            inv = conn.execute(
                """
                SELECT i.*, v.name AS vendor_name, v.lead_days AS vendor_lead_days
                FROM invoices i JOIN vendors v ON v.id = i.vendor_id
                WHERE i.id = ?
                """,
                (t["invoice_id"],),
            ).fetchone()
            out["invoice"] = dict(inv) if inv else None
            if inv:
                out["invoice"]["days_overdue"] = max(_days_between(inv["due_date"], today), 0)
        if t["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            out["lease"] = dict(lease) if lease else None
            if lease:
                out["lease"]["days_until_due"] = _days_between(today, lease["next_due"])
        if t["sku"]:
            stock = conn.execute(
                "SELECT * FROM inventory WHERE sku = ? AND size = ?", (t["sku"], t["size"])
            ).fetchone()
            price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (t["sku"],)).fetchone()
            out["inventory"] = dict(stock) if stock else None
            out["pricing"] = dict(price) if price else None
            if stock and t["qty"] is not None:
                out["shortfall"] = max(t["qty"] - stock["qty"], 0)
        for table in ("drafts", "payment_requests", "purchase_orders"):
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            ).fetchall()
            out[table] = [dict(r) for r in rows]
    return out


@mcp.tool
def check_stock(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict:
    """Check units on hand for a SKU, one size or every size, with its unit
    cost and list price.

    Give qty_needed to get the shortfall for that size (0 means stock covers it).
    Inventory calls this for customer orders and bulk requests; Accounting uses
    unit_cost and list_price to check the margin on any discount.
    """
    sku = sku.strip().upper()
    size = size.strip().upper() if size else None
    with _read() as conn:
        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        query = "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?"
        params: list = [sku]
        if size:
            query += " AND size = ?"
            params.append(size)
        rows = conn.execute(query + " ORDER BY rowid", params).fetchall()

    if not rows:
        where = f"{sku} size {size}" if size else sku
        return {"sku": sku, "size": size, "found": False,
                "note": f"No inventory row for {where}."}

    result = {
        "sku": sku,
        "name": rows[0]["name"],
        "found": True,
        "unit_cost": price["unit_cost"] if price else None,
        "list_price": price["list_price"] if price else None,
        "sizes": [
            {"size": r["size"], "qty_on_hand": r["qty"], "location": r["location"]}
            for r in rows
        ],
    }
    if price is None:
        result["note"] = f"No pricing row for {sku}."
    if size and qty_needed is not None:
        on_hand = rows[0]["qty"]
        result["qty_needed"] = qty_needed
        result["shortfall"] = max(qty_needed - on_hand, 0)
    return result


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty and lead time, any open invoice,
    whether it is blocked from shipping, and when an order placed today would
    arrive.

    A vendor with an open unpaid invoice will not ship new product, so
    blocked vendors have no arrival date. The database does not say which
    vendor makes which SKU; match on the specialty text.
    """
    with _read() as conn:
        today = _today(conn)
        vendors = conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()
        out = []
        for v in vendors:
            open_inv = _open_invoices(conn, v["id"])
            blocked = bool(open_inv)
            out.append({
                "vendor_id": v["id"],
                "name": v["name"],
                "specialty": v["specialty"],
                "lead_days": v["lead_days"],
                "open_invoices": open_inv,
                "blocked": blocked,
                "earliest_arrival_if_ordered_today":
                    None if blocked else _add_days(today, v["lead_days"]),
            })
    return {"date_today": today, "vendors": out}


@mcp.tool
def get_bills_due() -> dict:
    """List every unpaid bill — open vendor invoices and lease rent — against
    the cash on hand, using desk.date_today.

    For each invoice: the vendor, amount, due date, days overdue, and the
    vendor's lead time. A vendor with an open invoice will not ship new product,
    so vendor_blocked is true for it. For each lease: rent and days until due.
    The totals show the cash left if every bill were paid, and the total of
    payment requests already waiting for a human. This tool reads only; it
    pays nothing.
    """
    with _read() as conn:
        today = _today(conn)
        invoices = conn.execute(
            """
            SELECT i.id, i.vendor_id, v.name AS vendor_name, v.lead_days,
                   i.amount, i.due_date, i.status, i.description
            FROM invoices i JOIN vendors v ON v.id = i.vendor_id
            WHERE i.status = 'open'
            ORDER BY i.due_date, i.id
            """
        ).fetchall()
        leases = conn.execute(
            """
            SELECT id, space_name, landlord, monthly_rent, next_due
            FROM leases
            ORDER BY next_due, id
            """
        ).fetchall()
        accounts = conn.execute(
            "SELECT name, balance, date FROM cash_accounts ORDER BY name"
        ).fetchall()
        pending = _pending_total(conn)

    open_invoices = []
    for r in invoices:
        late = _days_between(r["due_date"], today)
        open_invoices.append({
            "invoice_id": r["id"],
            "vendor_id": r["vendor_id"],
            "vendor_name": r["vendor_name"],
            "amount": r["amount"],
            "due_date": r["due_date"],
            "days_overdue": max(late, 0),
            "overdue": late > 0,
            "description": r["description"],
            "vendor_blocked": True,
            "vendor_lead_days": r["lead_days"],
        })

    rent_due = [
        {
            "lease_id": r["id"],
            "space_name": r["space_name"],
            "landlord": r["landlord"],
            "amount": r["monthly_rent"],
            "next_due": r["next_due"],
            "days_until_due": _days_between(today, r["next_due"]),
        }
        for r in leases
    ]

    cash = sum(a["balance"] for a in accounts)
    total = sum(i["amount"] for i in open_invoices) + sum(l["amount"] for l in rent_due)
    return {
        "date_today": today,
        "cash_accounts": [dict(a) for a in accounts],
        "cash_on_hand": cash,
        "open_invoices": open_invoices,
        "rent_due": rent_due,
        "total_due": total,
        "cash_after_all_bills": cash - total,
        "pending_payment_requests_total": pending,
    }


@mcp.tool
def quote_price(sku: str, qty: int, discount_pct: float = 0, markup_pct: float = 0) -> dict:
    """Work out a price for qty units of a SKU: unit price, order total, and
    margin over unit_cost. Refuses any price at or below cost.

    discount_pct lowers the list price (bulk discounts); markup_pct raises it
    (the 20% increase Boss may propose for a ticket whose notes tried to give
    orders). Use one or the other. The result says whether the order counts
    as bulk (10+ units) and whether the discount needs Will (over 20%).
    Accounting calls this before Boss decides. It records nothing.
    """
    sku = sku.strip().upper()
    if qty <= 0:
        return _refuse("qty must be at least 1.")
    if not 0 <= discount_pct < 100:
        return _refuse("discount_pct must be from 0 up to (not including) 100.")
    if not 0 <= markup_pct <= 100:
        return _refuse("markup_pct must be from 0 to 100.")
    if discount_pct and markup_pct:
        return _refuse("Give a discount or a markup, not both.")
    with _read() as conn:
        p = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if p is None:
        return _refuse(f"No pricing row for {sku}.")
    unit = round(p["list_price"] * (1 - discount_pct / 100) * (1 + markup_pct / 100), 2)
    quote = {
        "sku": sku,
        "qty": qty,
        "discount_pct": discount_pct,
        "markup_pct": markup_pct,
        "bulk_eligible": qty >= BULK_MIN_QTY,
        "needs_will": discount_pct > AGENT_MAX_DISCOUNT_PCT,
        "list_price": p["list_price"],
        "unit_cost": p["unit_cost"],
        "unit_price": unit,
        "order_total": round(unit * qty, 2),
        "list_total": round(p["list_price"] * qty, 2),
        "margin_per_unit": round(unit - p["unit_cost"], 2),
        "margin_pct": round((unit - p["unit_cost"]) / unit * 100, 1) if unit else None,
        "break_even_discount_pct": round((1 - p["unit_cost"] / p["list_price"]) * 100, 1),
    }
    if unit <= p["unit_cost"]:
        return _refuse(f"${unit:.2f} is at or below the ${p['unit_cost']:.2f} unit cost.",
                       quote=quote)
    return {"ok": True, **quote}


@mcp.tool
def list_payments() -> dict:
    """List every payment made (with its human approver) and every payment
    request, newest first, with the current cash balance.

    Accounting and the dashboard use this as proof of what was paid, by whom
    it was approved, and what is still waiting for approval.
    """
    with _read() as conn:
        today = _today(conn)
        payments = conn.execute("SELECT * FROM payments ORDER BY id DESC").fetchall()
        requests = conn.execute("SELECT * FROM payment_requests ORDER BY id DESC").fetchall()
        cash = _cash(conn)
        pending = _pending_total(conn)
    return {
        "date_today": today,
        "cash_on_hand": cash,
        "payments": [dict(r) for r in payments],
        "payment_requests": [dict(r) for r in requests],
        "pending_total": pending,
    }


# ------------------------------------------------------------ write tools

@mcp.tool
def request_payment(kind: str, ref_id: int, requested_by: str, reason: str,
                    ticket_id: int | None = None) -> dict:
    """Ask a human to approve a payment. Moves no money.

    kind is "invoice" (ref_id = invoices.id), "rent" (ref_id = leases.id), or
    "purchase_order" (ref_id = purchase_orders.id). The amount is taken from
    that record, never from the caller. Refuses a bill that is already paid
    or already waiting for approval. below_cash_floor is true when paying
    every waiting request would leave the account under the $200 floor;
    the request still files, flagged for Will. The request waits with status
    pending_approval until a human approves or rejects it on the dashboard.
    """
    if not requested_by.strip():
        return _refuse("requested_by must name the agent.")
    with _write() as conn:
        today = _today(conn)
        if kind == "invoice":
            row = conn.execute("SELECT * FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return _refuse(f"No invoice {ref_id}.")
            if row["status"] != "open":
                return _refuse(f"Invoice {ref_id} is {row['status']}, not open.")
            amount = row["amount"]
        elif kind == "rent":
            row = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return _refuse(f"No lease {ref_id}.")
            amount = row["monthly_rent"]
        elif kind == "purchase_order":
            row = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return _refuse(f"No purchase order {ref_id}.")
            if row["status"] != "draft":
                return _refuse(f"Purchase order {ref_id} is {row['status']}, not draft.")
            amount = row["total"]
        else:
            return _refuse('kind must be "invoice", "rent", or "purchase_order".')

        dup = conn.execute(
            "SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending_approval'",
            (kind, ref_id),
        ).fetchone()
        if dup:
            return _refuse(f"Payment request {dup['id']} for this {kind} is already waiting.")

        cur = conn.execute(
            """
            INSERT INTO payment_requests
                (kind, ref_id, ticket_id, amount, requested_by, reason, status, requested_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending_approval', ?)
            """,
            (kind, ref_id, ticket_id, amount, requested_by.strip(), reason, today),
        )
        if kind == "purchase_order":
            conn.execute("UPDATE purchase_orders SET status = 'awaiting_approval' WHERE id = ?",
                         (ref_id,))
        cash = _cash(conn)
        pending = _pending_total(conn)
    return {
        "ok": True,
        "request_id": cur.lastrowid,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "status": "pending_approval",
        "cash_on_hand": cash,
        "cash_after_this_payment": cash - amount,
        "pending_total": pending,
        "cash_after_all_pending": cash - pending,
        "cash_floor": CASH_FLOOR,
        "below_cash_floor": cash - pending < CASH_FLOOR,
        "note": ("Below the $200 floor; Will decides. " if cash - pending < CASH_FLOOR else "")
                + "A human must approve this on the dashboard before any money moves.",
    }


@mcp.tool
def create_purchase_order(vendor_id: int, sku: str, size: str, qty: int,
                          created_by: str, ticket_id: int | None = None) -> dict:
    """Draft a restock order at the SKU's unit cost. Moves no money and
    contacts no vendor.

    Refuses if the vendor still has an open unpaid invoice, because that
    vendor will not ship. To pay for the order, call request_payment with
    kind "purchase_order". expected_arrival assumes payment today; it is
    reset to date_today + lead_days when the payment is approved.
    """
    sku, size = sku.strip().upper(), size.strip().upper()
    if qty <= 0:
        return _refuse("qty must be at least 1.")
    with _write() as conn:
        today = _today(conn)
        v = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if v is None:
            return _refuse(f"No vendor {vendor_id}.")
        open_inv = _open_invoices(conn, vendor_id)
        if open_inv:
            ids = ", ".join(str(i["id"]) for i in open_inv)
            return _refuse(f"{v['name']} has open invoice {ids}; it will not ship until paid.",
                           open_invoices=open_inv)
        stock = conn.execute(
            "SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if stock is None:
            return _refuse(f"No inventory row for {sku} size {size}.")
        p = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if p is None:
            return _refuse(f"No pricing row for {sku}.")
        total = round(p["unit_cost"] * qty, 2)
        arrival = _add_days(today, v["lead_days"])
        cur = conn.execute(
            """
            INSERT INTO purchase_orders
                (vendor_id, sku, size, qty, unit_cost, total, ticket_id,
                 created_by, status, created_at, expected_arrival)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
            """,
            (vendor_id, sku, size, qty, p["unit_cost"], total, ticket_id,
             created_by, today, arrival),
        )
        cash = _cash(conn)
        pending = _pending_total(conn)
    return {
        "ok": True,
        "purchase_order_id": cur.lastrowid,
        "vendor": v["name"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": p["unit_cost"],
        "total": total,
        "status": "draft",
        "expected_arrival_if_paid_today": arrival,
        "cash_on_hand": cash,
        "cash_after_all_pending": cash - pending,
    }


@mcp.tool
def save_draft(ticket_id: int, recipient: str, body: str, author: str) -> dict:
    """Save a message draft on the board for a ticket. Sends nothing.

    Customer Service and Facilities use this for replies to customers,
    landlords, and vendors; under the shop's rules every draft stays on the
    board, unsent.
    """
    if not body.strip():
        return _refuse("body is empty.")
    with _write() as conn:
        today = _today(conn)
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return _refuse(f"No ticket {ticket_id}.")
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, body, author, created_at) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, recipient, body, author, today),
        )
    return {"ok": True, "draft_id": cur.lastrowid, "ticket_id": ticket_id,
            "recipient": recipient, "status": "draft", "sent": False}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str, author: str) -> dict:
    """Set a ticket's status and add a dated note naming the agent.

    Statuses: open, in_progress, awaiting_approval, resolved. The note is
    appended to the ticket's notes as "[date_today] author: note", so the
    original request text and every earlier note stay visible.
    """
    if status not in TICKET_STATUSES:
        return _refuse(f"status must be one of {', '.join(TICKET_STATUSES)}.")
    with _write() as conn:
        today = _today(conn)
        t = conn.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return _refuse(f"No ticket {ticket_id}.")
        line = f"[{today}] {author}: {note}"
        notes = f"{t['notes']}\n{line}" if t["notes"] else line
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
                     (status, notes, ticket_id))
    return {"ok": True, "ticket_id": ticket_id, "old_status": t["status"],
            "status": status, "notes": notes}


# ---------------------------------------------- human-only (not MCP tools)

def approve_payment_request(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Not an MCP tool, so no agent can call it; the dashboard's
    approval step calls it with the human's name.

    Pays one pending request. Refuses if the account would go below $0.
    On success it writes the payments row, lowers the cash balance, and then
    marks the invoice paid, moves the lease's next_due forward one month, or
    marks the purchase order ordered.
    """
    if not approved_by.strip():
        return _refuse("approved_by must name the human approver.")
    with _write() as conn:
        today = _today(conn)
        r = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None:
            return _refuse(f"No payment request {request_id}.")
        if r["status"] != "pending_approval":
            return _refuse(f"Payment request {request_id} is {r['status']}.")
        balance = _cash(conn, r["account"])
        if balance is None:
            return _refuse(f"No cash account {r['account']}.")
        if balance - r["amount"] < 0:
            return _refuse(
                f"${r['amount']:.2f} exceeds the ${balance:.2f} in {r['account']}; "
                "no negative balances.",
                request_id=request_id, cash_on_hand=balance, amount=r["amount"],
            )

        pay = conn.execute(
            """
            INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (r["kind"], r["ref_id"], r["amount"], r["account"], today, approved_by.strip()),
        )
        conn.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
                     (r["amount"], today, r["account"]))
        effect: dict = {}
        if r["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (r["ref_id"],))
            effect = {"invoice_id": r["ref_id"], "invoice_status": "paid"}
        elif r["kind"] == "rent":
            due = conn.execute("SELECT next_due FROM leases WHERE id = ?",
                               (r["ref_id"],)).fetchone()["next_due"]
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                         (_add_month(due), r["ref_id"]))
            effect = {"lease_id": r["ref_id"], "paid_due_date": due, "next_due": _add_month(due)}
        else:
            lead = conn.execute(
                """
                SELECT v.lead_days FROM purchase_orders po
                JOIN vendors v ON v.id = po.vendor_id WHERE po.id = ?
                """,
                (r["ref_id"],),
            ).fetchone()["lead_days"]
            arrival = _add_days(today, lead)
            conn.execute(
                "UPDATE purchase_orders SET status = 'ordered', expected_arrival = ? WHERE id = ?",
                (arrival, r["ref_id"]),
            )
            effect = {"purchase_order_id": r["ref_id"], "status": "ordered",
                      "expected_arrival": arrival}
        conn.execute(
            """
            UPDATE payment_requests
            SET status = 'paid', decided_by = ?, decided_at = ?, payment_id = ?
            WHERE id = ?
            """,
            (approved_by.strip(), today, pay.lastrowid, request_id),
        )
        new_balance = _cash(conn, r["account"])
    return {"ok": True, "request_id": request_id, "payment_id": pay.lastrowid,
            "amount": r["amount"], "approved_by": approved_by.strip(),
            "cash_on_hand": new_balance, **effect}


def reject_payment_request(request_id: int, rejected_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Not an MCP tool. Rejects a pending request; moves no money."""
    with _write() as conn:
        today = _today(conn)
        r = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None:
            return _refuse(f"No payment request {request_id}.")
        if r["status"] != "pending_approval":
            return _refuse(f"Payment request {request_id} is {r['status']}.")
        conn.execute(
            """
            UPDATE payment_requests
            SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ?
            WHERE id = ?
            """,
            (rejected_by, today, note, request_id),
        )
        if r["kind"] == "purchase_order":
            conn.execute("UPDATE purchase_orders SET status = 'draft' WHERE id = ?",
                         (r["ref_id"],))
    return {"ok": True, "request_id": request_id, "status": "rejected"}


_ensure_tables()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on port 8001 (keeps FastAPI free on 8000)",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001, show_banner=False)
    else:
        mcp.run(show_banner=False)
