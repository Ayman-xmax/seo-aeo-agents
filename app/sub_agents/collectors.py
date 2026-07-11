# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Phase-1 data collectors (run in parallel, I/O-bound).

Each writes a distinct output_key so the ParallelAgent fan-out has no write race.
`google_search` is isolated in serp_aeo (it cannot coexist with FunctionTools).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

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
    get_crux,
    inspect_url,
    retrieve_knowledge,
    run_pagespeed,
    semrush_status,
)
from ..tools.local_seo_mcp import build_local_seo_mcp
from ..tools.semrush_mcp import build_semrush_toolset


def _leaf(**kw) -> LlmAgent:
    """Collectors never delegate — lock transfer off."""
    kw.setdefault("disallow_transfer_to_peers", True)
    kw.setdefault("disallow_transfer_to_parent", True)
    kw.setdefault("before_tool_callback", governance_before_tool)
    return LlmAgent(**kw)


def create_competitor_discovery() -> LlmAgent:
    semrush = build_semrush_toolset(["organic_research", "overview_research"])
    local = build_local_seo_mcp()
    tools = [semrush_status] + ([local] if local else []) + ([semrush] if semrush else [])
    return _leaf(
        name="competitor_discovery",
        model=build_model(WORKER_MODEL),
        description="Identifies the site's real SEO competitors from keyword overlap.",
        instruction=contract(
            role="Identify the target site's true SEO competitors (not the user's "
            "business rivals) by who ranks for the niche's keywords.",
            must=[
                "FREE PATH (no subscription): use serp_competitors on 3-5 head queries "
                "from the niche to see which domains rank; aggregate the most frequent "
                "domains as competitors.",
                "If Semrush is configured, also use it for keyword-overlap confirmation.",
                "Return 3-5 competitors max, each with the evidence (which queries).",
                "If neither serp_competitors (DataForSEO) nor Semrush is configured, say "
                "so via semrush_status and report what's missing.",
            ],
            must_not=[
                "Invent competitor domains or overlap numbers.",
                "Analyze on-page/technical issues (other agents own that).",
            ],
            if_unsure="Return an empty competitor list and note 'data unavailable'.",
            skill_name="competitor_discovery",
        ),
        tools=tools,
        output_key=S.COMPETITOR_REPORT,
    )


def create_technical_audit() -> LlmAgent:
    return _leaf(
        name="technical_audit",
        model=build_model(WORKER_MODEL),
        description="Audits technical + on-page SEO: crawlability, CWV, robots/sitemap, "
        "canonical, schema, and crawlable-link/anchor hygiene.",
        instruction=contract(
            role="Run a technical + on-page SEO audit of the target site's key pages.",
            must=[
                "For each page: call audit_technical_basics and audit_links; run "
                "check_robots_and_sitemap once for the site.",
                "Use get_crux/run_pagespeed for Core Web Vitals where possible.",
                "Report each issue with the exact tool field it came from (evidence).",
                "Apply the crawlable-link rules literally: flag non-anchor href, "
                "onclick-only, javascript: hrefs, generic/stuffed anchors, missing "
                "alt/title, chained links, and >150 links/page.",
            ],
            must_not=[
                "Estimate Core Web Vitals or page counts.",
                "Recommend content/keyword strategy (other agents own that).",
                "Write to or modify the site.",
            ],
            if_unsure="Mark the specific check 'unavailable' and continue.",
            skill_name="technical_audit",
        ),
        tools=[audit_technical_basics, audit_links, check_robots_and_sitemap,
               get_crux, run_pagespeed, inspect_url],
        output_key=S.TECH_REPORT,
        after_tool_callback=harvest_signals_after_tool,
    )


def create_keyword_research() -> LlmAgent:
    semrush = build_semrush_toolset(["keyword_research", "organic_research"])
    local = build_local_seo_mcp()
    tools = [semrush_status] + ([local] if local else []) + ([semrush] if semrush else [])
    return _leaf(
        name="keyword_research",
        model=build_model(WORKER_MODEL),
        description="Researches keywords (free autocomplete + optional Semrush) and clusters them by intent.",
        instruction=contract(
            role="Research keywords for the niche and cluster them by search intent "
            "for the target site.",
            must=[
                "FREE PATH (no subscription): use keyword_ideas and question_keywords to "
                "generate a large list of REAL search queries from seed topics; use "
                "autocomplete to refine.",
                "Group keywords into intent-based clusters and map each cluster to a "
                "target URL to avoid cannibalization.",
                "If Semrush is configured, enrich clusters with its volume/difficulty/gap "
                "data; otherwise cluster on the free query lists WITHOUT volumes.",
                "Report volumes/difficulty ONLY when a tool returned them.",
            ],
            must_not=[
                "Invent search volumes or difficulty scores — the free tools don't provide "
                "them, so leave them blank rather than guessing.",
                "Perform technical or backlink analysis.",
            ],
            if_unsure="Cluster the free keyword ideas and note that volume/difficulty needs a paid source.",
            skill_name="keyword_research",
        ),
        tools=tools,
        output_key=S.KEYWORD_REPORT,
    )


def create_backlink() -> LlmAgent:
    semrush = build_semrush_toolset(["backlink_research", "overview_research"])
    tools = [semrush_status, retrieve_knowledge] + ([semrush] if semrush else [])
    return _leaf(
        name="backlink",
        model=build_model(WORKER_MODEL),
        description="Analyzes backlinks/gap (if a paid index is set) or gives a grounded "
        "authority-building strategy (free) otherwise.",
        instruction=contract(
            role="Analyze the target's backlink profile and gap vs competitors when a "
            "paid link index is available; otherwise produce a grounded authority plan.",
            must=[
                "If Semrush is configured: profile backlinks + gap (DR>=50, dofollow, "
                "min 1,000 monthly traffic, links all competitors have).",
                "FREE FALLBACK (no paid link index exists for backlinks): use "
                "retrieve_knowledge to produce a grounded authority/link-building STRATEGY "
                "— digital PR, unlinked-mention reclamation, brand mentions, HARO/Featured "
                "— and cite the guidance.",
                "Treat authority scores (DR/DA/AS) as relative proxies, never ground truth.",
            ],
            must_not=[
                "Invent referring domains or authority numbers.",
                "Present strategy as if it were live backlink data.",
                "Recommend buying links or any manipulative tactic.",
            ],
            if_unsure="Give best-practice authority strategy from the knowledge base and "
            "state clearly that live backlink data needs a paid source.",
            skill_name="backlink",
        ),
        tools=tools,
        output_key=S.BACKLINK_REPORT,
    )


def create_serp_aeo() -> LlmAgent:
    # ISOLATED: google_search cannot be mixed with FunctionTools in one agent.
    return _leaf(
        name="serp_aeo",
        model=build_model(WORKER_MODEL),
        description="Analyzes live SERP features and AI-Overview citation patterns.",
        instruction=contract(
            role="Analyze the live SERP for the niche's head terms: which SERP "
            "features appear (AI Overviews, PAA, featured snippets, sitelinks) and "
            "which domains get cited in AI answers.",
            must=[
                "Use google_search to observe real results for the target queries.",
                "Note when an AI Overview is present (discount click potential).",
                "Report which competitors are cited in AI answers, if visible.",
            ],
            must_not=[
                "Fabricate SERP features or citations you did not observe.",
                "Call any other tool (this agent only has search).",
            ],
            if_unsure="Report only what the search results actually show.",
            skill_name="serp_aeo",
        ),
        tools=[google_search],
        output_key=S.SERP_REPORT,
    )
