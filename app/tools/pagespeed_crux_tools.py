# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""PageSpeed Insights + CrUX field Core Web Vitals.

CrUX = cheap real-user field data (what Google actually uses to rank); PSI/
Lighthouse = lab diagnostics. Both degrade gracefully to `unavailable` when no
API key is configured, so the agent reports honestly instead of guessing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

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


def run_lighthouse(url: str, strategy: str) -> dict:
    """Measure REAL lab Core Web Vitals locally with headless Chrome — no API key needed.

    This is the ORGANIC path: we run Lighthouse ourselves instead of calling Google's
    PageSpeed API. Returns LCP, CLS and TBT (the lab proxy for INP) plus the performance
    score, each rated against Google's thresholds. Requires Node.js + Chrome (local).

    Args:
        url: The page to measure.
        strategy: 'mobile' (what Google indexes) or 'desktop'.
    """
    if not url.startswith(("http://", "https://")):
        return {"status": "error", "reason": "url must start with http:// or https://"}
    npx = shutil.which("npx")
    if not npx:
        return {"status": "unavailable",
                "reason": "Node.js/npx not found — install Node to measure CWV locally."}

    outdir = tempfile.mkdtemp(prefix="lh_")
    out = os.path.join(outdir, "lh.json")
    cmd = [
        npx, "-y", "lighthouse@12", url,
        "--output=json", f"--output-path={out}", "--quiet",
        "--only-categories=performance",
        "--chrome-flags=--headless=new --no-sandbox --disable-gpu --ignore-certificate-errors",
    ]
    if strategy.lower().startswith("desk"):
        cmd.append("--preset=desktop")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240,
                              shell=(os.name == "nt"))
        if not os.path.exists(out):
            err = (proc.stderr or proc.stdout or "").strip()[:200]
            return {"status": "unavailable",
                    "reason": f"Lighthouse produced no report: {err or 'unknown error'}"}
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
    except subprocess.TimeoutExpired:
        return {"status": "unavailable", "reason": "Lighthouse timed out (slow page)."}
    except Exception as e:
        return {"status": "unavailable", "reason": f"Lighthouse failed: {e}"}
    finally:
        shutil.rmtree(outdir, ignore_errors=True)

    audits = data.get("audits", {})
    perf = (data.get("categories", {}).get("performance", {}) or {}).get("score")
    metrics: dict = {}
    lcp_ms = audits.get("largest-contentful-paint", {}).get("numericValue")
    if lcp_ms is not None:
        lcp_s = round(float(lcp_ms) / 1000, 2)
        metrics["LCP_S"] = {"value": lcp_s, "rating": _classify("LCP_S", lcp_s)}
    cls = audits.get("cumulative-layout-shift", {}).get("numericValue")
    if cls is not None:
        metrics["CLS"] = {"value": round(float(cls), 3),
                          "rating": _classify("CLS", float(cls))}
    tbt = audits.get("total-blocking-time", {}).get("numericValue")
    if tbt is not None:
        tbt = round(float(tbt))
        metrics["TBT_MS"] = {"value": tbt,
                             "rating": "good" if tbt <= 200 else "poor" if tbt > 600 else "ni"}

    return {
        "status": "success",
        "url": url,
        "strategy": strategy,
        "lab_performance_score": round(perf * 100) if perf is not None else None,
        "metrics": metrics,
        "source": "local_lighthouse",
        "note": "Lab data measured locally with headless Chrome (no API key). TBT is the "
                "lab proxy for INP; true INP/field data needs real users (CrUX, Google-only).",
    }


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
