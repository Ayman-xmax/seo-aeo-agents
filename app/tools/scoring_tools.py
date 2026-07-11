# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Deterministic SEO/AEO Health Score.

The score is PURE CODE — no LLM judgment — so the before/after comparison is
objective and reproducible. It reads the `signals` bag (raw tool outputs
harvested by the after-tool callback) and aggregates per category. Categories
with no captured signal are marked `insufficient_data` and excluded from the
weighted overall (weights are renormalised over categories that have data), so
we never invent a number.
"""

from __future__ import annotations

from statistics import mean
from typing import Any
from urllib.parse import urlparse

from google.adk.tools.tool_context import ToolContext

from .. import config

SIGNALS_KEY = "signals"


def _signals(state) -> dict[str, list[dict]]:
    return dict(state.get(SIGNALS_KEY) or {})


def _score_technical(sig: dict[str, list[dict]]) -> tuple[float | None, dict, list[str]]:
    parts: list[float] = []
    detail: dict[str, float] = {}
    notes: list[str] = []
    # Core Web Vitals from CrUX field data.
    crux = [s for s in sig.get("get_crux", []) if s.get("status") == "success"]
    ratings = []
    for entry in crux:
        for _m, obj in (entry.get("metrics") or {}).items():
            r = obj.get("rating")
            ratings.append({"good": 100.0, "ni": 60.0, "poor": 20.0}.get(r, 50.0))
    if ratings:
        cwv = mean(ratings)
        parts.append(cwv)
        detail["core_web_vitals"] = round(cwv, 1)
    else:
        notes.append("No CrUX field data (set PAGESPEED_API_KEY) — CWV not scored.")
    # robots/sitemap hygiene.
    rs = [s for s in sig.get("check_robots_and_sitemap", []) if s.get("status") == "success"]
    if rs:
        pen = mean(min(len(s.get("findings", [])) * 15, 60) for s in rs)
        val = max(0.0, 100.0 - pen)
        parts.append(val)
        detail["robots_sitemap"] = round(val, 1)
    # canonical/indexability basics.
    tb = [s for s in sig.get("audit_technical_basics", []) if s.get("status") == "success"]
    if tb:
        def tpen(s):
            f = s.get("findings", [])
            return sum(20 if ("canonical" in x or "invalid" in x) else 8 for x in f)
        val = max(0.0, 100.0 - mean(min(tpen(s), 60) for s in tb))
        parts.append(val)
        detail["indexability_basics"] = round(val, 1)
    return (round(mean(parts), 1) if parts else None), detail, notes


def _score_on_page(sig: dict[str, list[dict]]) -> tuple[float | None, dict, list[str]]:
    parts: list[float] = []
    detail: dict[str, float] = {}
    notes: list[str] = []
    tb = [s for s in sig.get("audit_technical_basics", []) if s.get("status") == "success"]
    if tb:
        def oppen(s):
            f = s.get("findings", [])
            w = {"missing_title": 25, "missing_h1": 20, "multiple_h1": 10,
                 "missing_meta_description": 12}
            return sum(next((v for k, v in w.items() if x.startswith(k)), 8) for x in f)
        val = max(0.0, 100.0 - mean(min(oppen(s), 80) for s in tb))
        parts.append(val)
        detail["titles_meta_headings"] = round(val, 1)
    links = [s for s in sig.get("audit_links", []) if s.get("status") == "success"]
    if links:
        def lpen(s):
            base = min(s.get("issue_count", 0) * 4, 70)
            return base + (15 if s.get("over_link_limit") else 0)
        val = max(0.0, 100.0 - mean(min(lpen(s), 85) for s in links))
        parts.append(val)
        detail["link_anchor_health"] = round(val, 1)
    if not parts:
        notes.append("No page-level crawl signals captured yet.")
    return (round(mean(parts), 1) if parts else None), detail, notes


def _score_aeo(sig: dict[str, list[dict]]) -> tuple[float | None, dict, list[str]]:
    detail: dict[str, float] = {}
    notes: list[str] = []
    tb = [s for s in sig.get("audit_technical_basics", []) if s.get("status") == "success"]
    if not tb:
        notes.append("No structured-data/answer signals captured yet.")
        return None, detail, notes
    # Proxy: pages carrying useful entity schema score higher on machine-readability.
    scored = []
    for s in tb:
        types = set(s.get("schema_types", []))
        useful = types & config.RICH_RESULT_SCHEMA_TYPES
        val = 40.0 + min(len(useful) * 20.0, 60.0)
        scored.append(val)
    val = mean(scored)
    detail["structured_data_readiness"] = round(val, 1)
    notes.append("AEO score here is on-page schema readiness only; add AI share-of-"
                 "voice tracking (aeo_specialist) for the full picture.")
    return round(val, 1), detail, notes


def _score_content_keyword(sig: dict[str, list[dict]]) -> tuple[float | None, dict, list[str]]:
    """Content depth & structure from our own content crawl (deterministic)."""
    ac = [s for s in sig.get("audit_content", []) if s.get("status") == "success"]
    if not ac:
        return None, {}, ["Run audit_content on the target's key pages to score content "
                          "depth. Keyword-targeting vs the map stays qualitative; exact "
                          "volumes need Google Ads Keyword Planner (free)."]

    def page_score(s: dict) -> float:
        w = s.get("word_count", 0)
        score = 100.0
        if w < 300:
            score -= 55
        elif w < 600:
            score -= 25
        f = s.get("findings", [])
        if "no_h2_structure" in f:
            score -= 15
        if "no_extractable_formatting_for_aeo" in f:
            score -= 10
        return max(0.0, score)

    val = round(mean(page_score(s) for s in ac), 1)
    return val, {"content_depth_structure": val}, [
        "Scores content depth/structure (word count, headings, extractable formatting). "
        "Keyword-map matching remains a qualitative check in the keyword report."]


def _target_domain(state) -> str:
    brief = state.get(config.S.PROJECT_BRIEF) or {}
    net = urlparse(brief.get("target_url", "")).netloc.lower()
    return net[4:] if net.startswith("www.") else net


def _score_off_page(sig, state) -> tuple[float | None, dict, list[str]]:
    """Off-page authority from OUR OWN PageRank score (local link graph, no paid API).

    Reads the target's authority straight from the owned index (where bootstrap_authority
    /seed_index/compute_authority store it), which is more reliable than harvesting the
    MCP tool response. Falls back to any harvested domain_authority signals.
    """
    dom = _target_domain(state)
    if not dom:
        return None, {}, ["No target URL in the project brief to score off-page for."]

    rec, refs = None, []
    try:
        from seo_data_mcp import authority as _auth
        from seo_data_mcp import store as _store

        if not _store.get_authority(dom) and _store.all_edges():
            _auth.compute_pagerank()  # score the graph if it wasn't computed yet
        rec = _store.get_authority(dom)
        refs = _store.referring_domains(dom, 5000)
    except Exception:
        pass

    if rec and rec.get("score") is not None:
        val = round(float(rec["score"]), 1)
        return val, {"domain_authority_0_100": val,
                     "referring_domains_found": len(refs)}, [
            "PageRank authority over our own crawled link graph (log-normalized 0-100), "
            "the same mechanism as DR/AS but computed locally."]

    # Target isn't in the crawled graph = no inbound links discovered. Honest low floor
    # (NOT 'insufficient') — authority is real but undiscovered until we crawl who links here.
    return 15.0, {"referring_domains_found": 0}, [
        "MINIMAL/undiscovered off-page authority: no inbound links to this domain were "
        "found in the crawled graph (common for a site whose backlinks we haven't crawled "
        "— most sites link only internally). Run seed_common_crawl (free Common Crawl, the "
        "whole web's link graph) for a real web-scale authority number; the score rises as "
        "inbound links are discovered."]


def compute_health_score(label: str, tool_context: ToolContext) -> dict:
    """Compute the deterministic SEO/AEO Health Score from captured signals.

    Stores the scorecard in state as 'scorecard_baseline' or 'scorecard_after'.

    Args:
        label: 'baseline' (Phase 1) or 'after' (Phase 3).
    """
    state = tool_context.state
    sig = _signals(state)

    scorers = {
        "technical": _score_technical(sig),
        "on_page": _score_on_page(sig),
        "content_keyword": _score_content_keyword(sig),
        "off_page": _score_off_page(sig, state),
        "aeo_geo": _score_aeo(sig),
    }

    categories = []
    weighted_sum = 0.0
    weight_used = 0.0
    for cat, (score, detail, notes) in scorers.items():
        w = config.SCORE_WEIGHTS[cat]
        if score is not None:
            weighted_sum += score * w
            weight_used += w
        categories.append({
            "category": cat,
            "score": score if score is not None else "insufficient_data",
            "weight": w,
            "signals": detail,
            "notes": notes,
        })

    overall = round(weighted_sum / weight_used, 1) if weight_used > 0 else None
    scorecard = {
        "label": label,
        "overall": overall,
        "coverage": round(weight_used, 2),
        "categories": categories,
        "computed_from": list(sig.keys()),
    }
    key = config.S.SCORECARD_BASELINE if label == "baseline" else config.S.SCORECARD_AFTER
    state[key] = scorecard
    return {"status": "success", "scorecard": scorecard}


def diff_scorecards(tool_context: ToolContext) -> dict:
    """Compare baseline vs after scorecards into a before/after delta report.

    Reads 'scorecard_baseline' and 'scorecard_after' from state.
    """
    state = tool_context.state
    before = state.get(config.S.SCORECARD_BASELINE)
    after = state.get(config.S.SCORECARD_AFTER)
    if not before or not after:
        return {"status": "unavailable",
                "reason": "Need both baseline and after scorecards (run Phase 1 and Phase 3)."}

    def cat_map(sc):
        return {c["category"]: c["score"] for c in sc.get("categories", [])}

    b, a = cat_map(before), cat_map(after)
    per_category: dict[str, Any] = {}
    for cat in config.SCORE_WEIGHTS:
        bs, as_ = b.get(cat), a.get(cat)
        if isinstance(bs, (int, float)) and isinstance(as_, (int, float)):
            per_category[cat] = round(as_ - bs, 1)
        else:
            per_category[cat] = "n/a"

    ob, oa = before.get("overall"), after.get("overall")
    return {
        "status": "success",
        "overall_before": ob,
        "overall_after": oa,
        "overall_delta": (round(oa - ob, 1) if isinstance(ob, (int, float))
                          and isinstance(oa, (int, float)) else "n/a"),
        "per_category": per_category,
    }
