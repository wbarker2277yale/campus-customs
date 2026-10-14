-- Tables the shop's original database lacks: payment requests waiting for a
-- human, purchase orders, and message drafts. All start empty; no data is
-- invented. Applied to campus_customs_new.db only (never the original), by
-- mcp_server/server.py on start-up and by data/reset_db.py after a reset.

CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('invoice', 'rent', 'purchase_order')),
    ref_id INTEGER NOT NULL,
    ticket_id INTEGER,
    amount REAL NOT NULL,
    account TEXT NOT NULL DEFAULT 'checking',
    requested_by TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending_approval', 'rejected', 'paid')),
    requested_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    size TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_cost REAL NOT NULL,
    total REAL NOT NULL,
    ticket_id INTEGER,
    created_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'awaiting_approval', 'ordered')),
    created_at TEXT NOT NULL,
    expected_arrival TEXT,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status = 'draft'),
    created_at TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
