# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""The 3-phase state machine.

Phase 1 DIAGNOSE  (read-only) : parallel collect -> synthesize -> baseline score.
Phase 2 IMPLEMENT (gated)     : refine loop (draft/critic) -> AEO -> implement.
Phase 3 VERIFY    (checks)    : re-crawl -> after score -> improvement report.

Each phase is a workflow agent exposed as a sub-agent of the root coordinator, so
control naturally returns to the human between phases (the built-in checkpoints).
"""

from __future__ import annotations

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from . import sub_agents as sa
from .config import COLLECTORS_MODE


def build_phase1_diagnose() -> SequentialAgent:
    collector_agents = [
        sa.create_competitor_discovery(),
        sa.create_technical_audit(),
        sa.create_keyword_research(),
        sa.create_backlink(),
        sa.create_serp_aeo(),
    ]
    # Sequential avoids the concurrent burst that triggers free-tier 429s; parallel
    # is faster when the provider has headroom (paid tier / OpenAI).
    if COLLECTORS_MODE == "sequential":
        collectors = SequentialAgent(
            name="collectors",
            description="Runs competitor, technical, keyword, backlink, and SERP/AEO "
            "analysis one at a time (rate-limit friendly).",
            sub_agents=collector_agents,
        )
    else:
        collectors = ParallelAgent(
            name="collectors",
            description="Runs competitor, technical, keyword, backlink, and SERP/AEO "
            "analysis concurrently.",
            sub_agents=collector_agents,
        )
    return SequentialAgent(
        name="phase1_diagnose",
        description="PHASE 1 — DIAGNOSE & STRATEGIZE (read-only): analyze, conclude, "
        "map, strategize, and compute the baseline Health Score.",
        sub_agents=[
            collectors,
            sa.create_strategy_synthesizer(),
            sa.create_aeo_specialist(),
            sa.create_scorer("baseline"),
        ],
    )


def build_phase2_implement() -> SequentialAgent:
    refine_loop = LoopAgent(
        name="optimization_loop",
        description="Draft -> critique -> refine until the quality gate passes.",
        max_iterations=3,
        sub_agents=[
            sa.create_content_optimizer(),
            sa.create_critic(),
        ],
    )
    return SequentialAgent(
        name="phase2_implement",
        description="PHASE 2 — IMPLEMENT (gated writes): refine the drafted changes, "
        "then apply the approved ones to the CMS and verify indexing.",
        sub_agents=[
            refine_loop,
            sa.create_implementation(),
        ],
    )


def build_phase3_verify() -> SequentialAgent:
    return SequentialAgent(
        name="phase3_verify",
        description="PHASE 3 — VERIFY & SCORE: re-crawl changed pages, recompute the "
        "Health Score, and report the before/after improvement.",
        sub_agents=[
            sa.create_verifier(),
            sa.create_scorer("after"),
            sa.create_improvement_reporter(),
            sa.create_monitoring(),
        ],
    )
