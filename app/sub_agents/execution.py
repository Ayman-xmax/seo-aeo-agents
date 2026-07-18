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
    commit_changes,
    compute_health_score,
    create_page,
    diff_scorecards,
    generate_sitemap,
    get_crux,
    gsc_opportunities,
    inspect_url,
    publish_change,
    push_changes,
    query_organic,
    replace_in_repo,
    search_analytics,
    write_robots,
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
            role="Apply the approved changes to the site, then verify. You can implement "
            "on-page, technical, content, and AEO changes end-to-end.",
            must=[
                "Only apply approved items; the write tools are blocked until "
                "state['publish_approved'] is True.",
                "To CHANGE an existing value (title, meta, H1, any copy), PREFER "
                "replace_in_repo(current_text, new_text) — it edits the value wherever it "
                "lives (HTML, React/Astro/Vue component, Hugo/Jekyll template, config), not "
                "just static HTML. Use the exact current value from the action plan.",
                "If replace_in_repo returns 'not_found', the value is build-generated or "
                "from a CMS — record it to the change-set (publish_change) and tell the user "
                "which file/component to edit.",
                "For ADDING things: create_page(...) for new pages; generate_sitemap(base_url) "
                "+ write_robots(sitemap_url) for the sitemap; publish_change for schema/meta "
                "insertion in static HTML.",
                "For NEW CONTENT in state['drafted_content'] (full articles the writer "
                "produced): create_page(path, title, meta_description, heading, body_html) "
                "for each — then add them to the sitemap.",
                "Apply exactly the values from the approved action plan / draft — verbatim.",
                "If a repo was cloned (state has site_repo_path): changes are written to the "
                "real files (result 'applied_to_file') on the 'seo-agent-optimizations' "
                "branch; then call commit_changes once with a clear message. Offer to "
                "push_changes so the user can open a pull request (nothing hits main/live "
                "until they merge). Only push after they say yes.",
                "If there is NO repo: changes go to the change-set (seo_changes/changeset.md). "
                "Say so CLEARLY and tell the user: to apply these to the live site, paste the "
                "repo URL (I'll clone and apply) or apply the change-set manually. Do NOT call "
                "commit_changes when there is no repo.",
                "inspect_url verification is OPTIONAL (needs GSC creds). If not configured, "
                "note it briefly and continue — it does NOT block applying changes.",
                "Report a clear summary: what was applied-to-file vs change-set, and the "
                "commit if any.",
            ],
            must_not=[
                "Publish anything not in the approved plan.",
                "Claim a page was indexed without an inspect_url verdict.",
                "Use Google's Indexing API for normal pages (it is JobPosting-only).",
                "Claim to have BUILT backlinks — you can draft outreach and find targets, "
                "but acquiring links is a human/PR activity, not something you execute.",
            ],
            if_unsure="Stop and ask for human confirmation before publishing.",
            skill_name="implementation",
            extra="APPROVED ON-PAGE DRAFT:\n{draft_changes?}\n\n"
            "NEW CONTENT TO PUBLISH (create_page each):\n{drafted_content?}",
        ),
        tools=[replace_in_repo, publish_change, generate_sitemap, write_robots,
               create_page, commit_changes, push_changes, inspect_url],
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
                "Call gsc_opportunities(site_url, 28) for REAL rankings/clicks; compare its "
                "totals to state['gsc_baseline'] (from Phase 1) for a genuine before/after "
                "when both exist.",
                "Also pull GA4 organic engagement and CrUX where creds exist.",
                "Report only tool-returned metrics; name unavailable sources.",
                "Be honest: ranking/traffic change takes weeks — a same-day re-pull confirms "
                "changes are live, not that rankings moved. Recommend a re-audit cadence.",
            ],
            must_not=[
                "Fabricate rankings, sessions, or citation metrics.",
                "Claim rankings improved from a same-day GSC pull.",
            ],
            if_unsure="Mark the metric source 'not_configured' and continue.",
            skill_name="monitoring",
        ),
        tools=[gsc_opportunities, search_analytics, query_organic, get_crux, inspect_url],
        before_tool_callback=governance_before_tool,
        after_tool_callback=harvest_signals_after_tool,
        disallow_transfer_to_peers=True,
        output_key=S.MONITORING_REPORT,
    )
