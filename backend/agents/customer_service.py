"""Customer Service: drafts messages for customers. Drafts stay on the board;
nothing is sent. Prompt: backend/prompts/customer_service.md.
"""

NAME = "customer_service"
ROLE = "Drafts messages to customers (saved on the board, never sent), using facts from the other agents."
MCP_TOOLS = ("get_ticket", "check_stock", "list_vendors", "save_draft")
