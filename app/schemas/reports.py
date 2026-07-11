# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Report + strategy schemas. Every Finding carries its data source so groundedness
is machine-checkable, not a matter of trust."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
Category = Literal["technical", "on_page", "content_keyword", "off_page", "aeo_geo"]


class Finding(BaseModel):
    """A single grounded observation."""

    title: str = Field(description="Short statement of the issue or opportunity.")
    category: Category
    severity: Severity
    evidence: str = Field(
        description="The concrete tool-output value this is based on (e.g. "
        "'crawler.audit_links.non_crawlable=4'). REQUIRED — no unbacked findings."
    )
    source: str = Field(
        description="Which tool/field produced the evidence, or 'unavailable'."
    )
    recommendation: str = Field(description="What to do about it.")


class RoadmapItem(BaseModel):
    """One prioritized action in the strategy roadmap."""

    action: str
    category: Category
    priority: int = Field(description="1 = highest.", ge=1)
    effort: Literal["low", "medium", "high"]
    expected_impact: Literal["low", "medium", "high"]
    target_urls: list[str] = Field(default_factory=list)
    rationale: str = Field(description="Grounded reason, citing a finding/source.")


class ContentBrief(BaseModel):
    """An auto-generated brief for a content/optimization task."""

    target_url: str
    primary_keyword: str
    secondary_keywords: list[str] = Field(default_factory=list)
    search_intent: Literal["informational", "navigational", "commercial", "transactional"]
    suggested_outline: list[str] = Field(default_factory=list)
    paa_questions: list[str] = Field(default_factory=list)
    aeo_answer_blocks: list[str] = Field(
        default_factory=list,
        description="40-60 word direct-answer blocks to lead sections (AEO).",
    )
    internal_link_targets: list[str] = Field(default_factory=list)


class StrategyRoadmap(BaseModel):
    """Phase-1 terminal output: conclusions + prioritized plan."""

    summary: str = Field(description="Plain-language conclusion, no jargon.")
    findings: list[Finding]
    roadmap: list[RoadmapItem]
    content_briefs: list[ContentBrief] = Field(default_factory=list)
    unavailable_data: list[str] = Field(
        default_factory=list,
        description="Checks that could not run (missing creds/quota) — stated honestly.",
    )
