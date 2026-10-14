"""Model, Portkey, and limits for every Campus Customs agent.

- MODEL_NAME is fixed to gpt-6-luna. It is deliberately not read from the
  environment, so no other model can reach any agent or run.
- build_model() makes one shared client through Portkey with PORTKEY_API_KEY.
- The limits below cap token use per ticket; output/harness.md explains each.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
PROMPTS = BACKEND / "prompts"
AUDIT_PATH = Path(os.environ.get("CC_AUDIT_PATH", ROOT / "output" / "audit_trail.json"))  # override only for tests

# The key lives in AI Foundations/.env (two folders up). Closest .env wins.
for folder in reversed([ROOT, *ROOT.parents][:3]):
    load_dotenv(folder / ".env", override=True)

MODEL_NAME = "gpt-6-luna"  # the only model allowed in this assignment
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")

# ---- token and loop limits (per ticket; shared by every agent in the chain)
MAX_REQUESTS_PER_TICKET = 30        # model calls, all agents combined
MAX_TOOL_CALLS_PER_TICKET = 40      # MCP tool calls plus delegations
MAX_TOKENS_PER_TICKET = 150_000     # input + output tokens, all agents combined
MAX_OUTPUT_TOKENS_PER_RESPONSE = 6_000  # includes the model's hidden reasoning tokens
MAX_DELEGATION_DEPTH = 3            # boss -> agent -> agent -> agent, no deeper
MAX_DELEGATIONS_PER_TICKET = 6
AUDIT_PREVIEW_CHARS = 800           # tool results are trimmed to this in the audit trail
MODEL_CALL_TIMEOUT_S = 15           # one model call; typical calls take 2-6 s, stragglers are retried
MODEL_CALL_RETRIES = 3              # retries on timeout or a Portkey 5xx error


def usage_limits() -> UsageLimits:
    return UsageLimits(
        request_limit=MAX_REQUESTS_PER_TICKET,
        tool_calls_limit=MAX_TOOL_CALLS_PER_TICKET,
        total_tokens_limit=MAX_TOKENS_PER_TICKET,
    )


# Reasoning summaries put each agent's reasons for a tool call or delegation into the audit trail.
# Low reasoning effort keeps each step quick; the reasoning summary still records why.
MODEL_SETTINGS = OpenAIResponsesModelSettings(
    max_tokens=MAX_OUTPUT_TOKENS_PER_RESPONSE,
    openai_reasoning_effort="low",
    openai_reasoning_summary="auto",
)


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to a .env in this project or a parent folder.")
    return key


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    """One shared gpt-6-luna client, through Portkey, for all five agents."""
    key = require_api_key()
    # Portkey latency is erratic (2-65 s for the same small call) and it sometimes returns 500.
    # Cut any call at 15 s and retry it, up to 3 times, so one straggler can't freeze the board.
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL,
                         default_headers={"x-portkey-api-key": key},
                         timeout=MODEL_CALL_TIMEOUT_S, max_retries=MODEL_CALL_RETRIES)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
