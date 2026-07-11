# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""AEO/GEO specialist — optimize for citation in AI answer engines."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import SYNTH_MODEL, S, build_model
from ..guardrails import contract, governance_before_tool
from ..tools import retrieve_knowledge


def create_aeo_specialist() -> LlmAgent:
    # RAG-grounded (no google_search here — it's isolated in serp_aeo).
    return LlmAgent(
        name="aeo_specialist",
        model=build_model(SYNTH_MODEL),
        description="Optimizes content to be cited by AI answer engines (AEO/GEO).",
        instruction=contract(
            role="Produce AEO/GEO recommendations so the site gets cited in AI "
            "Overviews, Perplexity, ChatGPT, and Gemini answers.",
            must=[
                "Apply the validated citation levers: answer-first 40-60 word blocks, "
                "question-shaped headings, cited statistics and quotations, entity/"
                "schema clarity, authoritative fluent voice.",
                "Recommend a maintained 'prompt panel' of category questions to track "
                "AI share-of-voice and citations over time.",
                "Use retrieve_knowledge and cite the guidance you rely on.",
                "Be explicit that traditional ranking gates AI citation — AEO sits on "
                "top of SEO, not instead of it.",
            ],
            must_not=[
                "Claim to control Google's index or reranker (not possible).",
                "Fabricate AI citations or share-of-voice numbers.",
                "Overstate llms.txt — note it is unproven and Google does not use it.",
                "Modify the site.",
            ],
            if_unsure="State that AI-citation data needs live prompt-panel tracking to confirm.",
            skill_name="aeo_specialist",
            extra="SERP/AEO OBSERVATIONS:\n{serp_report?}\n\nSTRATEGY:\n{strategy?}",
        ),
        tools=[retrieve_knowledge],
        before_tool_callback=governance_before_tool,
        output_key=S.AEO_REPORT,
    )
