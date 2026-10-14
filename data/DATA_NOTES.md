# Campus Customs Database Notes

**Files**
- `campus_customs.db` is the original database. Never write to it; it is the reset point.
- `campus_customs_new.db` is the working copy. The MCP server and backend read and write this file.
- **To reset:** copy `campus_customs.db` over `campus_customs_new.db`.

Both files start byte-identical (SHA-1 `f447ca6a…`). The database passes SQLite's integrity and foreign-key checks. It has no views or triggers.

---

## Shop state on "today" (`desk.date_today` = 2026-08-31)

| Item | Value |
|---|---|
| Cash (`checking`) | $3,400.00 |
| Open invoice 501 | $840.00 to Bulldog Print Co, due 2026-08-28, so **3 days overdue** |
| Rent (lease 1, Chapel Street shop) | $2,400.00 to Elm City Properties, due 2026-09-02 (in 2 days) |
| Payments made | none (the `payments` table is empty) |

Paying invoice 501 and the rent together costs $3,240, which leaves **$160**.

## Tables

| Table | Rows | What it holds |
|---|---|---|
| `desk` | 1 | `date_today` (the shop's "today") and `notes` |
| `tickets` | 3 | Open work items: `type`, `requester`, `subject`, an optional `sku`/`size`/`qty`, a `lease_id` or `invoice_id`, `status`, `notes`, and `created_at` |
| `inventory` | 10 | Stock per `(sku, size)`: `qty` and `location` |
| `pricing` | 4 | `unit_cost` and `list_price` for each SKU |
| `vendors` | 3 | `name`, `specialty`, and `lead_days` |
| `invoices` | 1 | Bills owed to vendors: `vendor_id`, `amount`, `due_date`, `status`, `description` |
| `leases` | 1 | `space_name`, `landlord`, `monthly_rent`, `next_due` |
| `cash_accounts` | 1 | `balance` and `date` for each account |
| `payments` | 0 | The payment ledger: `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` |

## Inventory and pricing

| SKU | Item | Sizes (qty) | Unit cost | List price | Margin |
|---|---|---|---|---|---|
| CC-HOOD-NAVY | Basic Hoodie Big Yale | S 4, M 8, L 14, XL 6 | $22.00 | $58.00 | 62% |
| CC-TEE-WHITE | Classic Bulldog Tee | **S 0**, M 5, L 3, XL 2 | $8.00 | $28.00 | 71% |
| CC-HAT-BLUE | Yale Cap | OS 40 | $6.00 | $22.00 | 73% |
| CC-MUG-CREST | Crest Mug | **OS 0** | $3.50 | $14.00 | 75% |

## Vendors

| ID | Vendor | Specialty | Lead time | Open invoice? |
|---|---|---|---|---|
| 1 | Bulldog Print Co | apparel reprint | 5 days | **Yes: #501, overdue. Will not ship until it is paid.** |
| 2 | Elm City Gifts | mugs and small goods | 3 days | No |
| 3 | QuickShip CT | local courier | 1 day | No |

## Open tickets

| # | Type | Requester | Request | What it runs into |
|---|---|---|---|---|
| 101 | `customer_order` | Tauhid Zaman | 1 Bulldog tee, size S | Size S is out of stock. A restock from Bulldog Print Co is blocked by invoice 501. The ticket links to `invoice_id` 501. |
| 102 | `rent_notice` | Elm City Properties | Rent due in 2 days | $2,400, lease 1. Paying it needs human approval. |
| 103 | `price_override` | Yale AI Club | 20 navy hoodies, size M, bulk discount | Only 8 in stock (12 short), and the restock is blocked by invoice 501. The discount must stay above the $22.00 unit cost. |

## How the tickets and tables connect

```
desk.date_today (2026-08-31) ── sets what counts as overdue / due soon
cash_accounts.checking $3,400 ── one pool that every payment draws from
│
├── Ticket 101  customer_order ── inventory (CC-TEE-WHITE, S) = 0
│                └─ invoice_id ──► invoices #501 ($840, overdue) ──► vendors #1 Bulldog Print Co
├── Ticket 102  rent_notice ───── lease_id ──► leases #1 ($2,400, due 09-02)
└── Ticket 103  price_override ── inventory (CC-HOOD-NAVY, M) = 8 of 20
                 └─ restock is apparel, so also Bulldog Print Co ──► blocked by #501
                 └─ discount ──► pricing (cost $22.00, list $58.00)
```

**Explicit links** (foreign keys in the data): 101 → invoice 501 → vendor 1; 102 → lease 1. Ticket 103 has no foreign key; it connects through `sku` and `size`.

**Hidden links** (business rules the data doesn't encode):
1. **Invoice 501 blocks both product tickets.** Both missing items are apparel, and Bulldog Print Co is the only apparel vendor. It ships nothing until #501 is paid. Paying #501 is therefore the first step for 101 *and* 103.
2. **All three tickets compete for the same $3,400.**

## Cash math

| Step | Amount | Running balance |
|---|---|---|
| Starting cash | | $3,400.00 |
| Pay invoice 501 (overdue) | −$840.00 | $2,560.00 |
| Pay rent, lease 1 (due 09-02) | −$2,400.00 | $160.00 |
| Restock 1 tee, size S, at $8.00 cost | −$8.00 | $152.00 |
| Restock 12 hoodies, size M, at $22.00 cost | −$264.00 | **−$112.00 ✗** |

All four can't be paid. Doing everything is **$112 short**, and the pay tool must refuse rather than go negative. No revenue comes in, so the Yale AI Club's purchase does not refill cash. Someone (Boss, with human approval) has to choose. Options:
- **Fill 103 partly:** 8 in M now, plus up to 6 more restocked ($132), and tell the club.
- **Substitute sizes:** 8 M plus 12 L from stock. There are 14 in L, and this needs no restock cash at all.
- **Hold the hoodie restock** until the club confirms, and keep the cash for rent.

Rent is a lease obligation due in 2 days and should not be skipped.

## Timing

| Event | Date |
|---|---|
| Today | 2026-08-31 (Mon) |
| Invoice 501 was due | 2026-08-28, already 3 days overdue |
| Rent due | 2026-09-02 |
| Earliest Bulldog Print delivery, if #501 is paid and an order placed today (5-day lead time) | 2026-09-05 |
| QuickShip CT local courier (1-day lead time) | for delivering to the customer once stock arrives |

## Ticket 103 discount bounds

| | Per hoodie | 20 hoodies |
|---|---|---|
| List price | $58.00 | $1,160.00 |
| Unit cost | $22.00 | $440.00 |
| Break-even discount | 62.1% off | |
| Example: 15% off | $49.30 (55% margin) | $986.00 |
| Example: 20% off | $46.40 (53% margin) | $928.00 |

The data sets no discount policy, so Accounting proposes one and Boss or the human approves it.

## Likely agent routing

| Ticket | Path through the agents | Needs human approval |
|---|---|---|
| 101 | Boss → Inventory (finds S out of stock, Bulldog blocked) → Accounting (prepares #501 payment and a tee PO) → Customer Service (drafts a message to Tauhid with ETA 09-05) | Yes: paying #501 |
| 102 | Boss → Facilities (checks lease 1 and the due date) → Accounting (prepares the $2,400 payment) | Yes: paying rent |
| 103 | Boss → Inventory (8 of 20 in stock, restock options) → Accounting (margin on the discount, cash check) → Boss (final call) → Customer Service (draft to Yale AI Club) | Yes, if a restock PO is paid |

## Odd things in the data

- **Invoice 501's description is "Rush reprint CC-TEE-WHITE S"**, yet stock for size S is still 0. Either those tees already sold, or the rush reprint never arrived. Ticket 101 points at this invoice, so the agents should notice the link and not assume the invoice covers new stock.
- **Ticket 101 is a single tee.** Its $20 margin is small next to the $840 invoice, but paying #501 is needed anyway because it unblocks 103 and it is overdue.

## Things to decide later

- **No purchase-order table.** Accounting is meant to "prepare purchase orders," but the schema has nowhere to store them. We need to decide where drafts and POs live: a new table, or notes on the ticket.
- **Status values.** Only `open` appears in `tickets.status` and `invoices.status`. The tools will need agreed values such as `in_progress`, `awaiting_approval`, `resolved`, and `paid`.
- **After rent is paid,** `leases.next_due` should probably move forward one month.
- **The mug is out of stock** (Elm City Gifts restocks it), but no ticket asks for it.
