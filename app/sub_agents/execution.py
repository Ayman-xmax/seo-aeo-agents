# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Phase-2/3 agents: implementation (gated), verification, monitoring, scoring.

Scoring is triggered here but computed deterministically in scoring_tools — the
LLM only calls the tool and relays its result verbatim, so the number can't drift.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import WORKER_MODEL, S, build_model
from ..guardrails import (
    contract,
    governance_before_tool,
    harvest_signals_after_tool,
)
from ..tools import (
    audit_links,
    audit_technical_basics,
    check_robots_and_sitemap,
    compute_health_score,
    diff_scorecards,
    get_crux,
    inspect_url,
    publish_change,
    query_organic,
    search_analytics,
)


def create_scorer(label: str) -> LlmAgent:
    """A minimal agent that runs the deterministic Health Score for `label`."""
    return LlmAgent(
        name=f"scorer_{label}",
        model=build_model(WORKER_MODEL),
        description=f"Computes the deterministic {label} Health Score.",
        instruction=contract(
            role=f"Compute the {label} SEO/AEO Health Score.",
            must=[
                f"Call compute_health_score exactly once with label='{label}'.",
                "Relay the tool's scorecard verbatim — overall, per-category, coverage.",
                "Name any category marked 'insufficient_data' and why.",
            ],
            must_not=[
                "Invent or adjust any score — the tool is the sole source of truth.",
            ],
            if_unsure="Report exactly what the tool returned.",
            skill_name="scorer",
        ),
        tools=[compute_health_score],
        before_tool_callback=governance_before_tool,
        disallow_transfer_to_peers=True,
        # Do NOT reuse the scorecard state key here — compute_health_score writes the
        # structured dict to S.SCORECARD_*; the agent's narrative goes to its own key so
        # it doesn't overwrite the dict that Phase 3's diff_scorecards depends on.
        output_key=f"scorecard_{label}_summary",
    )


def create_implementation() -> LlmAgent:
    return LlmAgent(
        name="implementation",
        model=build_model(WORKER_MODEL),
        description="Applies approved changes to the CMS (gated) and verifies indexing.",
        instruction=contract(
            role="Apply the approved drafted changes to the live site via publish_change, "
            "one field at a time, then verify index status.",
            must=[
                "Only apply items the user has approved; publish_change is blocked until "
                "state['publish_approved'] is True.",
                "Apply exactly the values in state['draft_changes'] — do not improvise.",
                "After publishing, use inspect_url to verify index/canonical status.",
                "Record every change (publish_change appends to change_log automatically).",
            ],
            must_not=[
                "Publish anything not in the approved draft.",
                "Claim a page was indexed without an inspect_url verdict.",
                "Use Google's Indexing API for normal pages (it is JobPosting-only).",
            ],
            if_unsure="Stop and ask for human confirmation before publishing.",
            skill_name="implementation",
            extra="APPROVED DRAFT:\n{draft_changes?}",
        ),
        tools=[publish_change, inspect_url],
        before_tool_callback=governance_before_tool,
        disallow_transfer_to_peers=True,
        output_key=S.CHANGE_LOG,
    )


def create_verifier() -> LlmAgent:
    """Phase-3 re-audit: refresh signals from the live site after changes."""
    return LlmAgent(
        name="verifier",
        model=build_model(WORKER_MODEL),
        description="Re-crawls changed pages to confirm changes are live and correct.",
        instruction=contract(
            role="Re-audit the pages that were changed to confirm the edits are live "
            "and technically correct.",
            must=[
                "Re-run audit_technical_basics and audit_links on the changed URLs "
                "(from change_log) and check_robots_and_sitemap for the site.",
                "Refresh Core Web Vitals via get_crux where available.",
                "Confirm each change_log item is reflected in the live page, or flag it.",
            ],
            must_not=[
                "Assume a change worked without re-crawling.",
                "Modify the site.",
            ],
            if_unsure="Flag the specific change as 'unverified'.",
            skill_name="verifier",
            extra="CHANGE LOG:\n{change_log?}",
        ),
        tools=[audit_technical_basics, audit_links, check_robots_and_sitemap, get_crux,
               inspect_url],
        before_tool_callback=governance_before_tool,
        after_tool_callback=harvest_signals_after_tool,
        disallow_transfer_to_peers=True,
        output_key="verification_report",
    )


def create_improvement_reporter() -> LlmAgent:
    return LlmAgent(
        name="improvement_reporter",
        model=build_model(WORKER_MODEL),
        description="Produces the before/after improvement report from the two scorecards.",
        instruction=contract(
            role="Produce the final before/after report: what was done, and what improved.",
            must=[
                "Call diff_scorecards once and relay the deltas verbatim.",
                "Tie each category delta to the specific change_log actions that caused it.",
                "State plainly, in non-technical language, what improved and what is next.",
            ],
            must_not=[
                "Invent improvement numbers — use only diff_scorecards output.",
                "Claim ranking/traffic gains that need weeks of data to confirm.",
            ],
            if_unsure="Report 'n/a' for any delta the tool could not compute.",
            skill_name="improvement_reporter",
            extra="CHANGE LOG:\n{change_log?}",
        ),
        tools=[diff_scorecards],
        before_tool_callback=governance_before_tool,
        disallow_transfer_to_peers=True,
        output_key="improvement_report",
    )


def create_monitoring() -> LlmAgent:
    return LlmAgent(
        name="monitoring",
        model=build_model(WORKER_MODEL),
        description="Pulls GSC/GA4/CrUX metrics and tracks ranks + AI citations over time.",
        instruction=contract(
            role="Report current organic performance and set up ongoing tracking.",
            must=[
                "Pull GSC Search Analytics, GA4 organic engagement, and CrUX where creds exist.",
                "Report only tool-returned metrics; name unavailable sources.",
                "Recommend a re-audit cadence and the AI share-of-voice prompt panel.",
            ],
            must_not=[
                "Fabricate rankings, sessions, or citation metrics.",
            ],
            if_unsure="Mark the metric source 'not_configured' and continue.",
            skill_name="monitoring",
        ),
        tools=[search_analytics, query_organic, get_crux, inspect_url],
        before_tool_callback=governance_before_tool,
        after_tool_callback=harvest_signals_after_tool,
        disallow_transfer_to_peers=True,
        output_key=S.MONITORING_REPORT,
    )
