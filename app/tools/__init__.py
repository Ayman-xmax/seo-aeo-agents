# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Tool functions for the SEO/AEO agents.

Deterministic tools (crawler, scoring) are ground truth. API-backed tools (GSC,
GA4, PageSpeed/CrUX, Semrush MCP) degrade to `unavailable`/`not_configured`
when creds are absent — never guessing. CMS publishing is gated.
"""

from .cms_publish_tools import publish_change
from .crawler_tools import (
    audit_content,
    audit_links,
    audit_technical_basics,
    check_robots_and_sitemap,
    fetch_site_overview,
)
from .ga4_tools import query_organic
from .gsc_tools import inspect_url, search_analytics
from .knowledge_retrieval import retrieve_knowledge
from .pagespeed_crux_tools import get_crux, run_pagespeed
from .repo_tools import clone_site_repo, commit_changes
from .scoring_tools import compute_health_score, diff_scorecards
from .semrush_mcp import build_semrush_toolset, semrush_status
from .site_build_tools import create_page, generate_sitemap, write_robots

__all__ = [
    "audit_content",
    "audit_links",
    "audit_technical_basics",
    "build_semrush_toolset",
    "check_robots_and_sitemap",
    "clone_site_repo",
    "commit_changes",
    "compute_health_score",
    "create_page",
    "diff_scorecards",
    "fetch_site_overview",
    "generate_sitemap",
    "get_crux",
    "inspect_url",
    "publish_change",
    "query_organic",
    "retrieve_knowledge",
    "run_pagespeed",
    "search_analytics",
    "semrush_status",
    "write_robots",
]
