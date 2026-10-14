"""Boss: reads each ticket, decides who works on it, and makes the final call.

Only Boss may change a ticket's status, so every decision passes through one
agent. Prompt: backend/prompts/boss.md.
"""

NAME = "boss"
ROLE = "Reads each ticket, decides who should work on it, and makes final calls; the only agent that sets ticket status."
MCP_TOOLS = ("list_open_tickets", "get_ticket", "get_bills_due", "list_payments", "update_ticket")
