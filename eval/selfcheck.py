# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Offline eval self-check for CI — validates the grading logic with NO model/network.

A cheap gate that runs on every push: it feeds the graders a known-good and known-bad
run and asserts they separate cleanly. This protects the eval harness itself from
regressions. The full live model eval (eval/run_eval.py) is a separate, optional job.

    uv run python -m eval.selfcheck   # exit 0 pass, 1 fail
"""

from __future__ import annotations

import sys

from eval.graders import grade_run

_GOOD_TRACE = [
    {"type": "tool_call", "agent": "root_agent", "tool": "fetch_site_overview"},
    {"type": "tool_call", "agent": "technical_audit", "tool": "audit_technical_basics"},
    {"type": "tool_call", "agent": "technical_audit", "tool": "audit_links"},
    {"type": "tool_call", "agent": "technical_audit", "tool": "audit_content"},
    {"type": "tool_call", "agent": "technical_audit", "tool": "run_lighthouse"},
    {"type": "message", "agent": "action_plan", "final": True,
     "text": 'Title: "AI Software Development Company | Holistic" (52 chars) -> current is X'},
]
_GOOD_STATE = {
    "project_brief": {"niche": "custom software development"},
    "scorecard_baseline": {"overall": 80, "coverage": 1.0, "categories": [
        {"category": c, "score": 70} for c in
        ("technical", "on_page", "content_keyword", "off_page", "aeo_geo")]},
}
_BAD_TRACE = [
    {"type": "tool_call", "agent": "root_agent", "tool": "set_project_brief"},
    {"type": "error", "message": "429 rate limit"},
]


def main() -> int:
    good = grade_run(_GOOD_TRACE, _GOOD_STATE)["overall"]
    bad = grade_run(_BAD_TRACE, {})["overall"]
    print(f"[selfcheck] good={good:.3f} bad={bad:.3f}")
    ok = good >= 0.90 and bad <= 0.20
    print("[selfcheck] PASS" if ok else "[selfcheck] FAIL — graders not separating runs")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
