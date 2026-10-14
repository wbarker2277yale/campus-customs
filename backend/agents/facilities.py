"""Facilities: handles the shop space side, such as leases and rent.
Prompt: backend/prompts/facilities.md.
"""

NAME = "facilities"
ROLE = "Handles the shop space: leases, rent amounts and due dates; asks Accounting to prepare rent payments. Writes nothing to the landlord (Will does)."
MCP_TOOLS = ("get_ticket", "get_bills_due")
