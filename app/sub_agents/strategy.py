# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Synthesis + content optimization agents (the 'conclude' and 'strategize' stages).

These reason over the collectors' reports and the RAG knowledge base. They do not
touch the site.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

from ..config import SYNTH_MODEL, WORKER_MODEL, S, build_model
from ..guardrails import contract, governance_before_tool
from ..tools import retrieve_knowledge


def submit_quality_verdict(passed: bool, score: int, notes: str,
                           tool_context: ToolContext) -> dict:
    """Record the critic's verdict; escalate (stop the refine loop) when passed.

    Args:
        passed: True if the draft meets the SEO+AEO quality bar.
        score: 0-100 quality score.
        notes: What still needs fixing (if not passed).
    """
    tool_context.state[S.CRITIQUE] = {"passed": passed, "score": score, "notes": notes}
    if passed:
        try:
            tool_context.actions.escalate = True  # stop the LoopAgent early
        except Exception:
            pass
    return {"status": "recorded", "passed": passed, "score": score}


def create_strategy_synthesizer() -> LlmAgent:
    return LlmAgent(
        name="strategy_synthesizer",
        model=build_model(SYNTH_MODEL),
        description="Merges all analysis into grounded conclusions + a prioritized roadmap.",
        instruction=contract(
            role="Synthesize the collectors' reports into plain-language conclusions "
            "and a prioritized SEO/AEO roadmap with content briefs.",
            must=[
                "Read the reports from state: competitor_report, tech_report, "
                "keyword_report, backlink_report, serp_report.",
                "Use retrieve_knowledge to ground recommendations in best-practice "
                "guidance and cite the source.",
                "Every finding must reference the report/field it came from.",
                "Output JSON matching the StrategyRoadmap shape: summary, findings[], "
                "roadmap[] (priority-ordered), content_briefs[], unavailable_data[].",
                "List every check that could not run under unavailable_data.",
            ],
            must_not=[
                "Introduce findings not supported by a report or knowledge passage.",
                "Recommend manipulative or against-guidelines tactics.",
                "Modify the site.",
            ],
            if_unsure="Put the item under unavailable_data instead of guessing.",
            skill_name="strategy_synthesizer",
            extra="Here are the analysis reports:\n"
            "COMPETITORS:\n{competitor_report?}\n\nTECHNICAL:\n{tech_report?}\n\n"
            "KEYWORDS:\n{keyword_report?}\n\nBACKLINKS:\n{backlink_report?}\n\n"
            "SERP/AEO:\n{serp_report?}",
        ),
        tools=[retrieve_knowledge],
        before_tool_callback=governance_before_tool,
        output_key=S.STRATEGY,
    )


def create_action_plan() -> LlmAgent:
    """Final Phase-1 step: present a clear, approvable action plan to the user."""
    return LlmAgent(
        name="action_plan",
        model=build_model(SYNTH_MODEL),
        description="Presents the Phase-1 action plan for the user to approve or refocus.",
        instruction=contract(
            role="Present the final Phase 1 ACTION PLAN in plain language so the user can "
            "approve it or choose a section to focus on first. This is the last thing they "
            "see in Phase 1.",
            must=[
                "Open with 2-3 sentences: what the site is (the niche you inferred), its "
                "overall Health Score, and the 2-3 biggest opportunities.",
                "Then a prioritized ACTION PLAN grouped by section — Technical, On-Page, "
                "Content, Off-Page, AEO. For each action give: WHAT you'll change, HOW "
                "you'll do it (the method), Priority (High/Med/Low), and Expected impact.",
                "Order sections by where the score is weakest / impact is highest.",
                "END with exactly this ask: 'Reply approve to implement the full plan, or "
                "tell me a section to focus on first (Technical / On-Page / Content / "
                "Off-Page / AEO).'",
            ],
            must_not=[
                "Introduce actions not supported by the findings/roadmap.",
                "Start implementing anything — Phase 1 is read-only.",
                "Dump raw JSON; write it for a human.",
            ],
            if_unsure="Present what the reports support and note any gaps honestly.",
            skill_name="action_plan",
            extra="ROADMAP:\n{strategy?}\n\nBASELINE SCORE:\n{scorecard_baseline?}\n\n"
            "AEO:\n{aeo_report?}\n\nCOMPETITORS:\n{competitor_report?}",
        ),
        before_tool_callback=governance_before_tool,
        output_key="action_plan",
    )


def create_content_optimizer() -> LlmAgent:
    return LlmAgent(
        name="content_optimizer",
        model=build_model(SYNTH_MODEL),
        description="Drafts concrete on-page + AEO content changes from the roadmap.",
        instruction=contract(
            role="Turn approved roadmap items into concrete, ready-to-apply on-page "
            "and AEO edits (titles, metas, headings, internal links, 40-60 word "
            "answer blocks, schema).",
            must=[
                "Work only from the roadmap in state['strategy'].",
                "If state['focus_section'] is set (and not 'all'), draft ONLY that section's "
                "items first; note the rest are deferred.",
                "Produce exact proposed values per target URL/field — do not apply them.",
                "Use retrieve_knowledge to follow current best practice and cite it.",
                "Respect pixel-aware title/meta length guidance.",
            ],
            must_not=[
                "Publish or modify the live site (that is the implementation agent, gated).",
                "Invent pages or facts about the business.",
            ],
            if_unsure="Flag the item as needing human input rather than guessing content.",
            skill_name="content_optimizer",
            extra="FOCUS SECTION (if any):\n{focus_section?}\n\nROADMAP:\n{strategy?}\n\n"
            "PRIOR CRITIQUE (if any):\n{critique?}",
        ),
        tools=[retrieve_knowledge],
        before_tool_callback=governance_before_tool,
        output_key=S.DRAFT_CHANGES,
    )


def create_critic() -> LlmAgent:
    return LlmAgent(
        name="critic",
        model=build_model(WORKER_MODEL),
        description="Scores the draft against the SEO+AEO checklist; ends the loop when it passes.",
        instruction=contract(
            role="Critically review the drafted changes against SEO best practice and "
            "the AEO citation levers, then submit a verdict.",
            must=[
                "Check: intent match, pixel-aware title/meta, heading hierarchy, "
                "answer-first blocks, schema validity, internal-link quality, grounding.",
                "Use retrieve_knowledge to verify against current guidance.",
                "Call submit_quality_verdict exactly once with passed/score/notes.",
                "Pass only when the draft is genuinely ready; otherwise list fixes.",
            ],
            must_not=[
                "Rewrite the content yourself (that is content_optimizer's job).",
                "Pass a draft that has unsupported claims or missing answer blocks.",
            ],
            if_unsure="Do not pass; return specific, actionable fixes.",
            skill_name="critic",
            extra="DRAFT:\n{draft_changes?}",
        ),
        tools=[retrieve_knowledge, submit_quality_verdict],
        before_tool_callback=governance_before_tool,
        output_key=S.CRITIQUE,
    )
