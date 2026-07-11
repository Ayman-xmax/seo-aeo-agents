# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Health Score schemas. The score is computed deterministically in
`tools/scoring_tools.py` — these models just carry the numbers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    category: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    signals: dict[str, float] = Field(
        default_factory=dict,
        description="The measured sub-signals that produced this score.",
    )
    notes: list[str] = Field(default_factory=list)


class ScoreCard(BaseModel):
    label: str = Field(description="'baseline' or 'after'.")
    overall: float = Field(ge=0, le=100)
    categories: list[CategoryScore]
    computed_from: list[str] = Field(
        default_factory=list,
        description="State reports the score was derived from (audit trail).",
    )


class ScoreDelta(BaseModel):
    """Before/after comparison — the '#6 score' deliverable."""

    overall_before: float
    overall_after: float
    overall_delta: float
    per_category: dict[str, float] = Field(
        default_factory=dict, description="category -> delta"
    )
    improvements: list[str] = Field(
        default_factory=list,
        description="What action drove each gain (ties deltas to change_log).",
    )
