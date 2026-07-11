# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Deterministic rules layer.

Exact SEO/AEO thresholds, API quotas, model tiers, and state keys. These are
*hard facts* — they live in code, never in the RAG knowledge base, so an agent
can never retrieve a fuzzy version of them (a "roughly 50k" sitemap limit is a
bug, not a nuance).
"""

from __future__ import annotations

import os

from google.adk.models import Gemini
from google.genai import types

# --------------------------------------------------------------------------- #
# Model tiers
# --------------------------------------------------------------------------- #
# Cheap/fast model for routing + I/O-bound collectors; a stronger tier for the
# synthesis/writing agents. Both default to flash so the prototype runs on a
# single AI Studio key; bump SYNTH_MODEL to a pro alias (e.g. "gemini-pro-latest")
# once you confirm it resolves against your account.
# All three are env-overridable so you can switch models (capacity/cost/quality)
# without touching code — e.g. SEO_WORKER_MODEL=gemini-flash-lite-latest if the
# default alias is temporarily overloaded (503) or rate-limited on the free tier.
ROUTER_MODEL = os.environ.get("SEO_ROUTER_MODEL", "gemini-flash-latest")
WORKER_MODEL = os.environ.get("SEO_WORKER_MODEL", "gemini-flash-latest")
SYNTH_MODEL = os.environ.get("SEO_SYNTH_MODEL", "gemini-flash-latest")


def build_model(name: str) -> Gemini:
    """Construct a Gemini model wrapper with sane retry defaults."""
    return Gemini(model=name, retry_options=types.HttpRetryOptions(attempts=3))


# --------------------------------------------------------------------------- #
# Session-state keys (single source of truth to avoid typos across agents)
# --------------------------------------------------------------------------- #
class S:
    PROJECT_BRIEF = "project_brief"           # niche, target_url, competitors, goals
    PHASE = "phase"                            # "diagnose" | "implement" | "verify"
    COMPETITOR_REPORT = "competitor_report"
    TECH_REPORT = "tech_report"
    KEYWORD_REPORT = "keyword_report"
    BACKLINK_REPORT = "backlink_report"
    SERP_REPORT = "serp_report"
    AEO_REPORT = "aeo_report"
    STRATEGY = "strategy"
    DRAFT_CHANGES = "draft_changes"
    CRITIQUE = "critique"
    CHANGE_LOG = "change_log"
    MONITORING_REPORT = "monitoring_report"
    SCORECARD_BASELINE = "scorecard_baseline"
    SCORECARD_AFTER = "scorecard_after"
    PUBLISH_APPROVED = "publish_approved"      # human gate for live writes
    QUOTA = "quota"                            # per-tool call counters


PHASE_DIAGNOSE = "diagnose"
PHASE_IMPLEMENT = "implement"
PHASE_VERIFY = "verify"

# --------------------------------------------------------------------------- #
# Tool-name governance sets (used by the runtime guardrail callback)
# --------------------------------------------------------------------------- #
# Tools that mutate the live site — blocked outside the implement phase.
WRITE_TOOL_NAMES = {"publish_change", "apply_seo_changes"}
# CMS write tools that additionally require explicit human approval.
CMS_PUBLISH_TOOL_NAMES = {"publish_change", "apply_seo_changes"}

# --------------------------------------------------------------------------- #
# Hard technical thresholds (Google Search Central + web.dev, verified 2025-26)
# --------------------------------------------------------------------------- #
SITEMAP_MAX_URLS = 50_000
SITEMAP_MAX_BYTES = 50 * 1024 * 1024          # 50 MB uncompressed
ROBOTS_MAX_BYTES = 500 * 1024                 # 500 KiB (rest ignored)
MAX_LINKS_PER_PAGE = 150
MAX_CLICK_DEPTH = 3

# Core Web Vitals "good" bands (75th percentile field data).
CWV_GOOD = {"LCP_S": 2.5, "INP_MS": 200, "CLS": 0.1}
CWV_POOR = {"LCP_S": 4.0, "INP_MS": 500, "CLS": 0.25}

# On-page length guidance. Google measures PIXELS, not characters; these char
# bands are the pragmatic proxies (title ~575px ≈ 60 chars, meta ~920px ≈ 158).
TITLE_CHARS = {"min": 30, "ideal_low": 50, "ideal_high": 60, "max": 65}
META_CHARS = {"min": 70, "ideal_low": 140, "ideal_high": 160, "max": 165}

# Structured-data types that still yield Google rich results (FAQ/HowTo dropped).
RICH_RESULT_SCHEMA_TYPES = {
    "Article", "BreadcrumbList", "Product", "Review", "AggregateRating",
    "Recipe", "VideoObject", "Organization", "LocalBusiness", "Event",
    "JobPosting", "Course", "Dataset", "SoftwareApplication",
}
# Parsed but no longer a SERP feature — still useful for LLM entity comprehension.
DEPRECATED_RICH_RESULT_TYPES = {"FAQPage", "HowTo"}

# Backlink-gap default quality filters (Ahrefs-style).
BACKLINK_GAP_FILTERS = {"min_dr": 50, "min_monthly_traffic": 1000, "dofollow_only": True}

# --------------------------------------------------------------------------- #
# External API daily/■ quotas — tracked in state so we never blow past them.
# --------------------------------------------------------------------------- #
API_QUOTAS = {
    "inspect_url": 2000,        # GSC URL Inspection: 2,000/day/site (tightest)
    "search_analytics": 1200,   # per-minute soft cap; treated as run budget
    "run_pagespeed": 25000,
    "get_crux": 150,
    "publish_change": 500,      # self-imposed safety cap on live writes per run
}

# --------------------------------------------------------------------------- #
# RAG knowledge-base config
# --------------------------------------------------------------------------- #
EMBED_MODEL = "gemini-embedding-001"
CHUNK_TARGET_CHARS = 1800       # research: ~1800-char chunks retrieve best
CHUNK_OVERLAP_CHARS = 200
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base", "vector_store")

# --------------------------------------------------------------------------- #
# Health Score weights (per category, must sum to 1.0)
# --------------------------------------------------------------------------- #
SCORE_WEIGHTS = {
    "technical": 0.25,
    "on_page": 0.20,
    "content_keyword": 0.20,
    "off_page": 0.15,
    "aeo_geo": 0.20,
}
