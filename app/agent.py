# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""SEO + AEO multi-agent system — root coordinator.

The coordinator handles intake, then routes the user through three checkpointed
phases (diagnose -> implement -> verify). It sets the phase and the publish-
approval gate ONLY on explicit user instruction; the runtime guardrail enforces
that writes are impossible otherwise.
"""

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.tools.tool_context import ToolContext

from . import config
from .config import ROUTER_MODEL, S, build_model
from .guardrails import contract, governance_before_tool, init_run_state
from .phases import (
    build_phase1_diagnose,
    build_phase2_implement,
    build_phase3_verify,
)
from .tools import fetch_site_overview, semrush_status


def set_project_brief(niche: str, target_url: str, competitors: str, goals: str,
                      tool_context: ToolContext) -> dict:
    """Record the project brief that drives the whole run.

    Args:
        niche: The market/topic the site wants to rank in.
        target_url: The target website's URL.
        competitors: Comma-separated known competitors (optional; '' if none).
        goals: The user's goals in plain language.
    """
    brief = {
        "niche": niche,
        "target_url": target_url,
        "competitors": [c.strip() for c in competitors.split(",") if c.strip()],
        "goals": goals,
    }
    # user: scope -> persists across sessions for this user (site config).
    tool_context.state["user:" + S.PROJECT_BRIEF] = brief
    tool_context.state[S.PROJECT_BRIEF] = brief
    return {"status": "recorded", "brief": brief}


def set_phase(phase: str, tool_context: ToolContext) -> dict:
    """Advance the workflow phase. Call ONLY when the user asks to proceed.

    Args:
        phase: One of 'diagnose', 'implement', 'verify'.
    """
    if phase not in (config.PHASE_DIAGNOSE, config.PHASE_IMPLEMENT, config.PHASE_VERIFY):
        return {"status": "error", "reason": f"Unknown phase '{phase}'."}
    tool_context.state[S.PHASE] = phase
    return {"status": "ok", "phase": phase}


def set_focus(section: str, tool_context: ToolContext) -> dict:
    """Record which section to prioritize in Phase 2. Call when the user picks one.

    Args:
        section: e.g. 'technical', 'on_page', 'content', 'off_page', 'aeo', or 'all'.
    """
    tool_context.state["focus_section"] = section
    return {"status": "ok", "focus_section": section}


def approve_publish(approved: bool, tool_context: ToolContext) -> dict:
    """Set the human publish-approval gate. Call ONLY on explicit user approval.

    Args:
        approved: True to allow live CMS writes for this run.
    """
    tool_context.state[S.PUBLISH_APPROVED] = bool(approved)
    return {"status": "ok", "publish_approved": bool(approved)}


root_agent = LlmAgent(
    name="root_agent",
    model=build_model(ROUTER_MODEL),
    description="SEO+AEO program coordinator: intake and 3-phase orchestration.",
    instruction=contract(
        role="You are the coordinator of an SEO + AEO optimization program. You run "
        "the user through three checkpointed phases and never skip a checkpoint.",
        must=[
            "You only need the target URL. If the user gives just a URL, call "
            "fetch_site_overview(url) to READ the site, then infer the niche and what the "
            "business does from its actual content — do not ask the user for the niche.",
            "Call set_project_brief with the target URL, the niche you inferred, any "
            "competitor URLs the user provided, and the goals. Briefly tell the user what "
            "you understood the site to be, so they can correct you.",
            "Explain the plan simply. Phase 1 (diagnose) is read-only and safe; run it "
            "by transferring to phase1_diagnose after set_phase('diagnose').",
            "Phase 1 ends by showing the user an ACTION PLAN. STOP and wait for their reply.",
            "When the user replies: if they name a section to focus on first, call "
            "set_focus(section). When they approve implementing, call set_phase('implement') "
            "(and approve_publish(true) only if they also approve applying changes to the "
            "site), then transfer to phase2_implement.",
            "After implementation, call set_phase('verify') and transfer to "
            "phase3_verify to produce the before/after report.",
            "Keep the user in plain language; no SEO jargon dumps.",
        ],
        must_not=[
            "Never call approve_publish(true) without the user's explicit approval.",
            "Never skip a phase or run implementation before the user approves the plan.",
            "Never fabricate results — the phase agents produce grounded reports.",
        ],
        if_unsure="Ask the user a short clarifying question rather than assuming.",
        skill_name="root_agent",
    ),
    tools=[fetch_site_overview, set_project_brief, set_phase, set_focus,
           approve_publish, semrush_status],
    sub_agents=[
        build_phase1_diagnose(),
        build_phase2_implement(),
        build_phase3_verify(),
    ],
    before_agent_callback=init_run_state,
    before_tool_callback=governance_before_tool,
)

app = App(
    root_agent=root_agent,
    name="app",
)
