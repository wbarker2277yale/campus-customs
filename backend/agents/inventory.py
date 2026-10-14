"""Inventory: checks stock by SKU and size, spots shortfalls, and works out
which vendor can restock. Prompt: backend/prompts/inventory.md.
"""

NAME = "inventory"
ROLE = "Checks stock by SKU and size, spots shortfalls, finds which vendor can restock, and drafts purchase orders."
MCP_TOOLS = ("get_ticket", "check_stock", "list_vendors", "create_purchase_order")
