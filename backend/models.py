"""Data types for the Campus Customs agent team.

- AgentName: the five agents; every agent may delegate to every other one
- AgentReport: the structured result every agent returns
- TicketRun: what one Boss run on one ticket produced
- RunBudget / TeamDeps: shared limits and context passed down a delegation chain
- AuditStep: one row of output/audit_trail.json
- RejectRequest / ResetRequest / RunAllRequest / ReflectionRequest: request bodies for backend/main.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[str, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

TicketStatus = Literal["open", "in_progress", "awaiting_approval", "resolved"]


class AgentReport(BaseModel):
    """What an agent hands back to whoever asked it (Boss or another agent)."""

    agent: AgentName
    ticket_id: int | None = Field(None, description="The ticket this work was for.")
    summary: str = Field(description="Two or three sentences: what was found and what was done.")
    facts_used: list[str] = Field(
        default_factory=list,
        description="Each fact relied on, with the tool it came from, e.g. "
                    "'check_stock: CC-TEE-WHITE size S has 0 on hand'.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Each write made, with its ID, e.g. 'request_payment: request 1 for invoice 501, $840'.",
    )
    needs_human_approval: bool = Field(
        False, description="True if a payment request is waiting for a human."
    )
    recommended_status: TicketStatus | None = Field(
        None, description="The status this agent recommends for the ticket."
    )
    open_questions: list[str] = Field(
        default_factory=list, description="Anything the agent could not settle from the data."
    )


class TicketRun(BaseModel):
    """The result of running the team on one ticket."""

    run_id: str
    ticket_id: int
    report: AgentReport | None = None
    stopped: str = Field(description='"completed", or why the run stopped early.')
    delegations: int = 0
    requests: int = 0
    total_tokens: int = 0


class AuditStep(BaseModel):
    """One step of an agent loop, as written to output/audit_trail.json."""

    time: str
    run_id: str
    ticket_id: int | None
    agent: Literal["boss", "inventory", "accounting", "facilities", "customer_service", "human", "report"]
    chain: list[str] = Field(description="Delegation path to this agent, e.g. ['boss', 'inventory'].")
    depth: int
    step: int = Field(description="Step number within this agent's own loop, from 1.")
    kind: Literal[
        "run_start", "model_request", "model_response", "tool_results",
        "delegation", "run_end", "limit_stop", "error", "ticket_done", "human_action",
        "resolution_record",
    ]
    model: str
    detail: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, int] = Field(
        default_factory=dict,
        description="Cumulative for the whole ticket run: requests, input/output/total tokens, tool calls.",
    )


@dataclass
class RunBudget:
    """Shared across every agent working one ticket, so limits apply to the whole chain."""

    delegations: int = 0


@dataclass
class TeamDeps:
    """Passed to every agent run; a delegated run gets a copy with a longer chain."""

    run_id: str
    ticket_id: int | None
    chain: list[str] = field(default_factory=list)
    budget: RunBudget = field(default_factory=RunBudget)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, description="Why Will rejected the payment.")


class ResetRequest(BaseModel):
    confirm: bool = Field(description="Must be true; the dashboard asks 'Are you sure?' first.")


class RunAllRequest(BaseModel):
    order: list[int] | None = Field(None, description="Ticket IDs in the order Will wants them worked.")


class ReflectionRequest(BaseModel):
    text: str = Field(min_length=1, description="Will's reflection, in his own words.")
