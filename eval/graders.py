# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Deterministic graders — score a run's trace + final state against the objective.

Each grader maps to one of the questions you want answered about a model:
  - FAILING            : did it error / not finish the phase?
  - NOT DOING IT       : did it skip a required tool/step?
  - LACKING            : did it only partially cover the objective?
  - OBJECTIVE QUALITY  : did it produce the deliverable properly (concrete plan, niche)?

Graders are pure functions of (trace, state) so they're testable offline without a model.
A `trace` is a list of {type, agent, tool, status, text, final} event dicts (as the
FastAPI /api/chat stream emits); `state` is the final session state.
"""

from __future__ import annotations

import re
from collections.abc import Callable

# Tools we expect a competent Phase-1 run to actually call.
_REQUIRED_TOOLS = {
    "audit_technical_basics", "audit_links", "audit_content", "run_lighthouse",
}
_CATEGORIES = ["technical", "on_page", "content_keyword", "off_page", "aeo_geo"]


def _tools_called(trace: list[dict]) -> set[str]:
    return {e.get("tool") for e in trace if e.get("type") == "tool_call" and e.get("tool")}


def _result(name: str, dimension: str, score: float, detail: str,
            weight: float = 1.0) -> dict:
    return {"grader": name, "dimension": dimension, "score": round(score, 3),
            "passed": score >= 0.999, "detail": detail, "weight": weight}


def g_phase_completed(trace: list[dict], state: dict) -> dict:
    sc = state.get("scorecard_baseline")
    ok = isinstance(sc, dict) and sc.get("overall") is not None
    return _result("phase_completed", "FAILING", 1.0 if ok else 0.0,
                   "Phase 1 produced a baseline Health Score"
                   if ok else "No scorecard — the run did not complete Phase 1", weight=2.0)


def g_no_errors(trace: list[dict], state: dict) -> dict:
    errs = [e for e in trace if e.get("type") == "error"]
    return _result("no_errors", "FAILING", 0.0 if errs else 1.0,
                   f"{len(errs)} error event(s)" if errs else "No errors in the run")


def g_required_tools(trace: list[dict], state: dict) -> dict:
    called = _tools_called(trace)
    hit = _REQUIRED_TOOLS & called
    missing = _REQUIRED_TOOLS - called
    return _result("required_tools", "NOT_DOING_IT", len(hit) / len(_REQUIRED_TOOLS),
                   f"missing: {sorted(missing)}" if missing else "all required tools called")


def g_category_coverage(trace: list[dict], state: dict) -> dict:
    sc = state.get("scorecard_baseline")
    if not isinstance(sc, dict):
        return _result("category_coverage", "LACKING", 0.0, "no scorecard")
    numeric = sum(1 for c in sc.get("categories", [])
                  if isinstance(c.get("score"), (int, float)))
    return _result("category_coverage", "LACKING", numeric / len(_CATEGORIES),
                   f"{numeric}/{len(_CATEGORIES)} categories scored numerically")


def g_niche_inferred(trace: list[dict], state: dict) -> dict:
    niche = (state.get("project_brief") or {}).get("niche")
    ok = bool(niche and niche.strip())
    return _result("niche_inferred", "OBJECTIVE_QUALITY", 1.0 if ok else 0.0,
                   f"niche = {niche!r}" if ok else "did not infer the site's niche")


def g_action_plan_specific(trace: list[dict], state: dict) -> dict:
    text = state.get("action_plan") or ""
    if not text.strip():
        # fall back to final messages captured in the trace
        text = "\n".join(e.get("text", "") for e in trace
                         if e.get("type") == "message" and e.get("final"))
    if not text.strip():
        return _result("action_plan_specific", "OBJECTIVE_QUALITY", 0.0, "no action plan")
    markers = 0
    markers += len(re.findall(r"->|→|current\s*[-→]", text, re.I)) > 0
    markers += len(re.findall(r"\d+\s*chars?", text, re.I)) > 0
    markers += len(re.findall(r"<title>|meta\s*name=|<h1>|application/ld\+json", text, re.I)) > 0
    markers += len(re.findall(r"[\"'][^\"']{15,}[\"']", text)) > 0  # a real quoted value
    return _result("action_plan_specific", "OBJECTIVE_QUALITY", markers / 4.0,
                   f"{markers}/4 specificity markers (exact values, char counts, tags)")


def g_grounding(trace: list[dict], state: dict) -> dict:
    """Reward honest degradation: when tools returned unavailable/not_configured, a
    grounded model surfaces that instead of inventing data. We can't detect fabrication
    perfectly offline, so we check the run acknowledged unavailable signals."""
    unavailable = [e for e in trace if e.get("type") == "tool_result"
                   and e.get("status") in ("unavailable", "not_configured", "not_found")]
    if not unavailable:
        return _result("grounding", "OBJECTIVE_QUALITY", 1.0,
                       "no unavailable tools to mishandle")
    final_text = " ".join(e.get("text", "") for e in trace
                          if e.get("type") == "message").lower()
    acknowledged = any(w in final_text for w in
                       ("unavailable", "not configured", "could not", "n/a", "insufficient"))
    return _result("grounding", "OBJECTIVE_QUALITY", 1.0 if acknowledged else 0.4,
                   "acknowledged unavailable data honestly" if acknowledged
                   else "had unavailable tools but didn't clearly flag them")


GRADERS: list[Callable[[list[dict], dict], dict]] = [
    g_phase_completed, g_no_errors, g_required_tools, g_category_coverage,
    g_niche_inferred, g_action_plan_specific, g_grounding,
]


def grade_run(trace: list[dict], state: dict) -> dict:
    """Run all graders; return per-grader results + weighted overall + metrics."""
    results = [g(trace, state) for g in GRADERS]
    tw = sum(r["weight"] for r in results)
    overall = sum(r["score"] * r["weight"] for r in results) / tw if tw else 0.0
    metrics = {
        "tool_calls": sum(1 for e in trace if e.get("type") == "tool_call"),
        "messages": sum(1 for e in trace if e.get("type") == "message"),
        "errors": sum(1 for e in trace if e.get("type") == "error"),
    }
    return {"overall": round(overall, 3), "results": results, "metrics": metrics}
