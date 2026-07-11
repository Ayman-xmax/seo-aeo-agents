# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""PageSpeed Insights + CrUX field Core Web Vitals.

CrUX = cheap real-user field data (what Google actually uses to rank); PSI/
Lighthouse = lab diagnostics. Both degrade gracefully to `unavailable` when no
API key is configured, so the agent reports honestly instead of guessing.
"""

from __future__ import annotations

import os

from .. import config

try:
    import requests

    _DEPS = True
except Exception:  # pragma: no cover
    _DEPS = False

_PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def _classify(metric: str, value: float) -> str:
    good, poor = config.CWV_GOOD, config.CWV_POOR
    if metric == "LCP_S":
        return "good" if value <= good["LCP_S"] else "poor" if value > poor["LCP_S"] else "ni"
    if metric == "INP_MS":
        return "good" if value <= good["INP_MS"] else "poor" if value > poor["INP_MS"] else "ni"
    if metric == "CLS":
        return "good" if value <= good["CLS"] else "poor" if value > poor["CLS"] else "ni"
    return "unknown"


def run_pagespeed(url: str, strategy: str) -> dict:
    """Run PageSpeed Insights (Lighthouse lab + CrUX field) for a URL.

    Args:
        url: The page to test.
        strategy: 'mobile' or 'desktop'. Mobile is what Google indexes.
    """
    if not _DEPS:
        return {"status": "unavailable", "reason": "requests not installed"}
    key = os.environ.get("PAGESPEED_API_KEY")
    params = {"url": url, "strategy": strategy, "category": "performance"}
    if key:
        params["key"] = key
    try:
        r = requests.get(_PSI_URL, params=params, timeout=60)
        if r.status_code != 200:
            return {"status": "unavailable", "reason": f"PSI HTTP {r.status_code}",
                    "hint": "Set PAGESPEED_API_KEY for higher quota."}
        data = r.json()
    except Exception as e:
        return {"status": "unavailable", "reason": f"PSI call failed: {e}"}

    lh = data.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    perf = (lh.get("categories", {}).get("performance", {}) or {}).get("score")
    return {
        "status": "success",
        "url": url,
        "strategy": strategy,
        "lab_performance_score": None if perf is None else round(perf * 100),
        "lab_lcp": audits.get("largest-contentful-paint", {}).get("displayValue"),
        "lab_cls": audits.get("cumulative-layout-shift", {}).get("displayValue"),
        "note": "Lab data cannot measure INP well — use CrUX (get_crux) for field INP.",
    }


def get_crux(url: str) -> dict:
    """Get 28-day field Core Web Vitals (LCP/INP/CLS) from the CrUX API.

    Args:
        url: The page (or origin) to query.
    """
    if not _DEPS:
        return {"status": "unavailable", "reason": "requests not installed"}
    key = os.environ.get("PAGESPEED_API_KEY") or os.environ.get("CRUX_API_KEY")
    if not key:
        return {"status": "unavailable",
                "reason": "CrUX requires an API key (set PAGESPEED_API_KEY/CRUX_API_KEY)."}
    try:
        r = requests.post(f"{_CRUX_URL}?key={key}", json={"url": url}, timeout=30)
        if r.status_code != 200:
            return {"status": "unavailable", "reason": f"CrUX HTTP {r.status_code} "
                    "(often means insufficient field data for this URL)."}
        metrics = r.json().get("record", {}).get("metrics", {})
    except Exception as e:
        return {"status": "unavailable", "reason": f"CrUX call failed: {e}"}

    out = {"status": "success", "url": url, "metrics": {}}
    mapping = {"largest_contentful_paint": ("LCP_S", 1000.0),
               "interaction_to_next_paint": ("INP_MS", 1.0),
               "cumulative_layout_shift": ("CLS", 1.0)}
    for api_name, (key_name, divisor) in mapping.items():
        p75 = metrics.get(api_name, {}).get("percentiles", {}).get("p75")
        if p75 is None:
            continue
        val = float(p75) / divisor
        out["metrics"][key_name] = {"p75": round(val, 3), "rating": _classify(key_name, val)}
    return out
