"""Accounting: watches cash and invoices, checks margins, and prepares
payments and purchase orders for human approval. The only agent that may
request a payment. Prompt: backend/prompts/accounting.md.
"""

NAME = "accounting"
ROLE = "Watches cash and invoices, checks margins on discounts, and prepares payments for human approval; the only agent that may request a payment."
MCP_TOOLS = ("get_ticket", "get_bills_due", "list_payments", "list_vendors", "check_stock",
             "quote_price", "request_payment")
