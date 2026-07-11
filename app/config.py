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
# Provider switch: "google" (Gemini, default) or "openai". Set SEO_LLM_PROVIDER.
# OpenAI routes through ADK's LiteLlm bridge and sidesteps Gemini free-tier 429s.
LLM_PROVIDER = os.environ.get("SEO_LLM_PROVIDER", "google").lower()

_MODEL_DEFAULTS = {
    "google": {"router": "gemini-flash-latest", "worker": "gemini-flash-latest",
               "synth": "gemini-flash-latest"},
    # gpt-4o-mini everywhere: high TPM (avoids gpt-4o's low 30k/min tier cap) + cheap.
    "openai": {"router": "openai/gpt-4o-mini", "worker": "openai/gpt-4o-mini",
               "synth": "openai/gpt-4o-mini"},
}
_d = _MODEL_DEFAULTS.get(LLM_PROVIDER, _MODEL_DEFAULTS["google"])

# Each tier is still env-overridable (capacity/cost/quality) without code changes.
ROUTER_MODEL = os.environ.get("SEO_ROUTER_MODEL", _d["router"])
WORKER_MODEL = os.environ.get("SEO_WORKER_MODEL", _d["worker"])
SYNTH_MODEL = os.environ.get("SEO_SYNTH_MODEL", _d["synth"])


def build_model(name: str):
    """Build a model wrapper for the active provider.

    Google -> Gemini (native). OpenAI/other -> LiteLlm (needs a litellm provider
    prefix like 'openai/gpt-4o-mini'; a bare name is assumed to be OpenAI).
    """
    is_litellm = LLM_PROVIDER != "google" or "/" in name or name.startswith("gpt-")
    if is_litellm:
        from google.adk.models.lite_llm import LiteLlm

        model = name if "/" in name else f"openai/{name}"
        return LiteLlm(model=model)
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

# Collector fan-out mode: "parallel" (fast, needs API headroom) or "sequential"
# (one collector at a time — survives free-tier per-minute rate limits / 429s).
COLLECTORS_MODE = os.environ.get("SEO_COLLECTORS_MODE", "parallel").lower()

# --------------------------------------------------------------------------- #
# Tool-name governance sets (used by the runtime guardrail callback)
# --------------------------------------------------------------------------- #
# Tools that mutate the live site — blocked outside the implement phase AND require
# explicit human approval (state['publish_approved']).
WRITE_TOOL_NAMES = {"publish_change", "apply_seo_changes", "generate_sitemap",
                    "write_robots", "create_page"}
CMS_PUBLISH_TOOL_NAMES = set(WRITE_TOOL_NAMES)

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
# Embeddings follow the LLM provider by default (override with SEO_EMBED_PROVIDER).
# IMPORTANT: if you switch provider, re-run `python -m app.knowledge_base.ingest`
# — embeddings from different models are NOT comparable.
EMBED_PROVIDER = os.environ.get("SEO_EMBED_PROVIDER", LLM_PROVIDER).lower()
_EMBED_DEFAULTS = {"google": "gemini-embedding-001", "openai": "text-embedding-3-small"}
EMBED_MODEL = os.environ.get(
    "SEO_EMBED_MODEL", _EMBED_DEFAULTS.get(EMBED_PROVIDER, "gemini-embedding-001")
)
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
