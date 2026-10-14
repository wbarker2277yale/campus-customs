"""The Campus Customs agent team: five PydanticAI agents with full connectivity.

- Every agent gets the same delegate(agent, task) tool, so any agent can hand
  work to any other agent (Boss included). Guardrails: no self-delegation, no
  delegating back up the current chain, a depth limit, and a per-ticket
  delegation limit.
- Every agent's shop facts and actions come from the campus-customs MCP server
  (mcp_server/server.py, attached in-process), filtered to that agent's own tools.
  There is no second shop-tools layer.
- Each agent loop runs with Agent.iter(), and every step is appended to
  output/audit_trail.json.
- All agents in one ticket share one usage counter, so the limits in
  agents/config.py apply to the whole chain.

run_ticket(ticket_id) works one ticket from Boss down; run_open_tickets()
works every open ticket, oldest first.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import replace
from functools import lru_cache
from typing import Any

from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import (
    RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.usage import RunUsage

from agents import accounting, audit, boss, customer_service, facilities, inventory
from agents.config import (
    MAX_DELEGATION_DEPTH, MAX_DELEGATIONS_PER_TICKET, MODEL_SETTINGS, PROMPTS, ROOT,
    build_model, usage_limits,
)
from models import AgentName, AgentReport, RunBudget, TeamDeps, TicketRun

MCP_DIR = ROOT / "mcp_server"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

TEAM = {m.NAME: m for m in (boss, inventory, accounting, facilities, customer_service)}
PROMPT_PLACEHOLDER = "AWAITING WILL'S WORDS"

# A fixed formatting rule added after every agent's own prompt (Will's words stay as written).
# Without it the model can spend minutes drafting its report as plain text before filing it.
FINISH_RULE = (
    "When your work is done, finish at once by calling final_result with your AgentReport. "
    "Keep the summary to two or three sentences. Never write the report as plain text first, "
    "and do not look anything up again just to write the report."
)


# ------------------------------------------------------------- MCP tools

@lru_cache(maxsize=1)
def _mcp() -> MCPToolset:
    """The campus-customs FastMCP server, attached in-process (one per backend)."""
    from server import mcp as campus_customs_mcp

    return MCPToolset(campus_customs_mcp)


def _tools_for(name: str):
    allowed = set(TEAM[name].MCP_TOOLS)
    return _mcp().filtered(lambda ctx, tool_def: tool_def.name in allowed)


# ------------------------------------------------------------- delegation

ROSTER = "\n".join(f"- {n}: {m.ROLE}" for n, m in TEAM.items())


async def delegate(ctx: RunContext[TeamDeps], agent: AgentName, task: str) -> dict[str, Any]:
    """Hand a task to another agent on the team and get its report back.

    Write the task so it stands alone: the ticket number, the facts you
    already have, and exactly what you need back. Team:
    {roster}
    """
    deps = ctx.deps
    me = deps.chain[-1]
    if agent == me:
        return {"refused": "An agent cannot delegate to itself."}
    if agent in deps.chain:
        return {"refused": f"{agent} is already working on this request higher up "
                           f"(chain: {' -> '.join(deps.chain)}); report back instead."}
    if len(deps.chain) >= MAX_DELEGATION_DEPTH + 1:
        return {"refused": f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; "
                           "finish with what you have."}
    if deps.budget.delegations >= MAX_DELEGATIONS_PER_TICKET:
        return {"refused": f"This ticket has used all {MAX_DELEGATIONS_PER_TICKET} delegations."}

    deps.budget.delegations += 1
    child = replace(deps, chain=[*deps.chain, agent])
    audit.append(deps, me, 0, "delegation",
                 {"to": agent, "task": task, "delegation_number": deps.budget.delegations},
                 ctx.usage)
    report = await run_agent(agent, task, child, usage=ctx.usage)
    return report.model_dump()


delegate.__doc__ = delegate.__doc__.format(roster=ROSTER)


# ------------------------------------------------------------- agents

def _prompt(name: str) -> str:
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    if PROMPT_PLACEHOLDER in text:
        raise RuntimeError(f"backend/prompts/{name}.md still holds a placeholder; "
                           "Will writes each prompt in his own words before any run.")
    return text


@lru_cache(maxsize=None)
def build_agent(name: str) -> Agent[TeamDeps, AgentReport]:
    return Agent(
        build_model(),
        name=name,
        deps_type=TeamDeps,
        output_type=AgentReport,
        instructions=[_prompt(name), FINISH_RULE],
        tools=[delegate],
        toolsets=[_tools_for(name)],
        model_settings=MODEL_SETTINGS,
    )


# ------------------------------------------------------------- the loop

def _audit_node(deps: TeamDeps, name: str, step: int, node: Any, usage: RunUsage) -> None:
    """Write one loop step to the audit trail."""
    if isinstance(node, ModelRequestNode):
        prompts, results = [], []
        for part in node.request.parts:
            if isinstance(part, UserPromptPart):
                prompts.append(audit.preview(part.content))
            elif isinstance(part, ToolReturnPart):
                results.append({"tool": part.tool_name, "call_id": part.tool_call_id,
                                "result": audit.preview(part.content)})
            elif isinstance(part, RetryPromptPart):
                results.append({"tool": part.tool_name, "call_id": part.tool_call_id,
                                "retry": audit.preview(part.content)})
        kind = "tool_results" if results else "model_request"
        audit.append(deps, name, step, kind,
                     {"user_prompt": prompts, "tool_results": results}, usage)
    elif isinstance(node, CallToolsNode):
        resp = node.model_response
        calls, text, thinking = [], [], []
        for part in resp.parts:
            if isinstance(part, ToolCallPart):
                calls.append({"tool": part.tool_name, "call_id": part.tool_call_id,
                              "args": part.args_as_dict()})
            elif isinstance(part, TextPart) and part.content:
                text.append(audit.preview(part.content))
            elif isinstance(part, ThinkingPart) and part.content:
                thinking.append(audit.preview(part.content))
        audit.append(deps, name, step, "model_response",
                     {"tool_calls": calls, "text": text, "thinking": thinking,
                      "finish_reason": resp.finish_reason,
                      "response_tokens": {"input": resp.usage.input_tokens,
                                          "output": resp.usage.output_tokens}},
                     usage)


async def run_agent(name: str, task: str, deps: TeamDeps,
                    usage: RunUsage | None = None) -> AgentReport:
    """Run one agent's loop on a task, auditing every step."""
    usage = usage if usage is not None else RunUsage()
    agent = build_agent(name)
    audit.append(deps, name, 0, "run_start", {"task": task}, usage)
    step = 0
    async with agent.iter(task, deps=deps, usage=usage, usage_limits=usage_limits()) as run:
        async for node in run:
            step += 1
            _audit_node(deps, name, step, node, usage)
        report = run.result.output
    report.agent = name
    audit.append(deps, name, step + 1, "run_end", {"report": report.model_dump()}, usage)
    return report


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, run_id: str | None = None) -> TicketRun:
    """Boss works one ticket; Boss delegates as needed. Every step is audited."""
    deps = TeamDeps(run_id=run_id or new_run_id(), ticket_id=ticket_id,
                    chain=["boss"], budget=RunBudget())
    usage = RunUsage()
    task = f"Work ticket {ticket_id}."
    report, stopped = None, "completed"
    try:
        report = await run_agent("boss", task, deps, usage=usage)
    except UsageLimitExceeded as exc:
        stopped = f"limit: {exc}"
        audit.append(deps, "boss", 0, "limit_stop", {"reason": str(exc)}, usage)
    except Exception as exc:  # recorded, never hidden
        stopped = f"error: {type(exc).__name__}: {exc}"[:400]
        audit.append(deps, "boss", 0, "error", {"reason": stopped}, usage)
    result = TicketRun(run_id=deps.run_id, ticket_id=ticket_id, report=report, stopped=stopped,
                       delegations=deps.budget.delegations, requests=usage.requests,
                       total_tokens=usage.total_tokens)
    audit.append(deps, "boss", 0, "ticket_done",
                 {"stopped": stopped, "delegations": result.delegations,
                  "final_status": report.recommended_status if report else None,
                  "summary": report.summary if report else None}, usage)
    return result


async def open_ticket_ids() -> list[int]:
    """Ask the MCP server (not the database directly) which tickets are not yet
    resolved: open, in progress, or awaiting approval. Oldest first."""
    from fastmcp import Client

    from server import mcp as campus_customs_mcp

    tickets = []
    async with Client(campus_customs_mcp) as client:
        for status in ("open", "in_progress", "awaiting_approval"):
            result = await client.call_tool("list_open_tickets", {"status": status})
            tickets += result.structured_content["tickets"]
    return [t["id"] for t in sorted(tickets, key=lambda t: (t["created_at"], t["id"]))]


async def run_open_tickets() -> list[TicketRun]:
    """The outer loop: work every open ticket, oldest first, one at a time."""
    return [await run_ticket(tid) for tid in await open_ticket_ids()]
