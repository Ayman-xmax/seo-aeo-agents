# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Guardrail layer — anti-hallucination and scope enforcement.

Two mechanisms:
  1. `contract(...)` builds a strict ROLE / MUST / MUST NOT / IF-UNSURE instruction
     block prepended to every agent, so no agent invents work outside its lane.
  2. Runtime callbacks enforce phase scope, quotas, and the human publish gate at
     tool-call time — instructions alone are never trusted for safety.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from . import config
from .config import S
from .skills import load_skill

# --------------------------------------------------------------------------- #
# Shared anti-hallucination preamble — attached to the top of every contract.
# --------------------------------------------------------------------------- #
ANTI_HALLUCINATION = (
    "GROUNDING RULES (non-negotiable):\n"
    "- Base every finding, number, URL, and recommendation ONLY on the output of "
    "your tools or values already present in session state. Cite the source field.\n"
    "- If a tool fails, returns `status: unavailable`, or the data is missing, say "
    "so explicitly and mark it `unavailable`. NEVER estimate, guess, or invent data.\n"
    "- Do not fabricate metrics, competitor names, keyword volumes, or backlinks.\n"
    "- If you are uncertain, say 'unknown' rather than producing a plausible answer.\n"
    "- Stay strictly within your ROLE. Do not perform another agent's job.\n"
)


def contract(
    role: str,
    must: list[str],
    must_not: list[str],
    if_unsure: str,
    extra: str = "",
    skill_name: str = "",
) -> str:
    """Build a guardrailed instruction block for an agent.

    If `skill_name` matches a file in app/skills/, that operating playbook is
    appended so the agent follows a proven methodology (higher productivity /
    efficiency) without bloating the code. Tune behaviour by editing the .md.
    """
    must_block = "\n".join(f"- {m}" for m in must)
    must_not_block = "\n".join(f"- {m}" for m in must_not)
    parts = [
        f"ROLE: {role}",
        "",
        ANTI_HALLUCINATION,
        "YOU MUST:",
        must_block,
        "",
        "YOU MUST NOT:",
        must_not_block,
        "",
        f"IF UNSURE OR DATA IS MISSING: {if_unsure}",
    ]
    skill = load_skill(skill_name) if skill_name else ""
    if skill:
        parts += ["", "OPERATING PLAYBOOK (follow this methodology):", skill]
    if extra:
        parts += ["", extra]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Runtime callback: initialise per-run state defaults.
# --------------------------------------------------------------------------- #
def init_run_state(callback_context: CallbackContext) -> None:
    """before_agent_callback on the root — seed default state once per run."""
    state = callback_context.state
    if state.get(S.PHASE) is None:
        state[S.PHASE] = config.PHASE_DIAGNOSE
    if state.get(S.QUOTA) is None:
        state[S.QUOTA] = {}
    if state.get(S.PUBLISH_APPROVED) is None:
        state[S.PUBLISH_APPROVED] = False


# --------------------------------------------------------------------------- #
# Runtime callback: govern every tool call (scope + quota + publish gate).
# --------------------------------------------------------------------------- #
def governance_before_tool(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
) -> dict | None:
    """before_tool_callback — returning a dict SKIPS the tool and uses the dict
    as its result. This is the hard safety boundary."""
    state = tool_context.state
    phase = state.get(S.PHASE, config.PHASE_DIAGNOSE)
    name = tool.name

    # 1) Read-only enforcement: no site mutations outside the implement phase.
    if name in config.WRITE_TOOL_NAMES and phase != config.PHASE_IMPLEMENT:
        return {
            "status": "blocked_read_only_phase",
            "reason": f"Tool '{name}' mutates the site but phase is '{phase}'. "
            "Writes are only allowed in the implement phase.",
        }

    # 2) Human publish gate: CMS writes require explicit approval.
    if name in config.CMS_PUBLISH_TOOL_NAMES and not state.get(S.PUBLISH_APPROVED):
        return {
            "status": "blocked_awaiting_approval",
            "reason": "Live publish requires human approval. Set "
            "state['publish_approved'] = True after the user approves the change.",
        }

    # 3) Quota tracking: block once a tool exceeds its configured daily budget.
    quota = dict(state.get(S.QUOTA) or {})
    limit = config.API_QUOTAS.get(name)
    used = quota.get(name, 0)
    if limit is not None and used >= limit:
        return {
            "status": "blocked_quota_exhausted",
            "reason": f"Tool '{name}' reached its quota ({limit}). Try again later "
            "or narrow the request.",
        }
    if limit is not None:
        quota[name] = used + 1
        state[S.QUOTA] = quota  # tracked delta -> persisted

    return None  # allow the call


# Deterministic tools whose raw output feeds the Health Score. Harvesting their
# ground-truth results into a `signals` bag is what lets scoring be pure code.
_HARVEST_TOOLS = {
    "audit_links",
    "audit_technical_basics",
    "check_robots_and_sitemap",
    "get_crux",
    "run_pagespeed",
    "inspect_url",
}


def harvest_signals_after_tool(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any
) -> dict | None:
    """after_tool_callback — capture deterministic tool outputs into state so the
    scoring engine computes from ground truth, not the model's prose."""
    if tool.name not in _HARVEST_TOOLS or not isinstance(tool_response, dict):
        return None
    signals = dict(tool_context.state.get("signals") or {})
    bucket = list(signals.get(tool.name, []))
    bucket.append(tool_response)
    signals[tool.name] = bucket[-50:]  # cap growth
    tool_context.state["signals"] = signals
    return None  # do not modify the tool result
