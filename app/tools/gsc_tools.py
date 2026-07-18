# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Google Search Console: URL Inspection (index status) + Search Analytics.

This is the ONLY reliable way to answer "is this URL indexed?" — Google's
Indexing API is JobPosting/Broadcast-only, so we verify, not force.

Requires a service account added as an owner/user of the GSC property, with its
JSON key path in GSC_SERVICE_ACCOUNT_FILE. Degrades to `not_configured` (never
guesses) when creds/libs are absent.
"""

from __future__ import annotations

import datetime
import os

from google.adk.tools.tool_context import ToolContext

_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _daterange(days: int) -> tuple[str, str]:
    end = datetime.date.today() - datetime.timedelta(days=2)  # GSC lags ~2 days
    start = end - datetime.timedelta(days=max(1, days))
    return start.isoformat(), end.isoformat()


def _service():
    """Build the Search Console API client, or return (None, reason)."""
    key_file = os.environ.get("GSC_SERVICE_ACCOUNT_FILE")
    if not key_file or not os.path.exists(key_file):
        return None, "GSC_SERVICE_ACCOUNT_FILE not set or file missing."
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception:
        return None, "google-api-python-client not installed (add it to run GSC live)."
    try:
        creds = service_account.Credentials.from_service_account_file(key_file, scopes=_SCOPES)
        return build("searchconsole", "v1", credentials=creds), None
    except Exception as e:
        return None, f"GSC auth failed: {e}"


def inspect_url(page_url: str, site_url: str) -> dict:
    """Inspect a URL's index status via the GSC URL Inspection API.

    Args:
        page_url: The full URL to inspect.
        site_url: The GSC property (e.g. 'https://example.com/' or 'sc-domain:example.com').
    """
    svc, reason = _service()
    if svc is None:
        return {"status": "not_configured", "reason": reason, "url": page_url}
    try:
        body = {"inspectionUrl": page_url, "siteUrl": site_url}
        res = svc.urlInspection().index().inspect(body=body).execute()
        idx = res.get("inspectionResult", {}).get("indexStatusResult", {})
        return {
            "status": "success",
            "url": page_url,
            "verdict": idx.get("verdict"),
            "coverage_state": idx.get("coverageState"),
            "google_canonical": idx.get("googleCanonical"),
            "user_canonical": idx.get("userCanonical"),
            "last_crawl_time": idx.get("lastCrawlTime"),
        }
    except Exception as e:
        return {"status": "unavailable", "reason": f"inspect failed: {e}", "url": page_url}


def search_analytics(site_url: str, start_date: str, end_date: str, dimension: str) -> dict:
    """Query GSC Search Analytics (clicks/impressions/ctr/position).

    Args:
        site_url: The GSC property.
        start_date: ISO date 'YYYY-MM-DD' (max 16 months history).
        end_date: ISO date 'YYYY-MM-DD'.
        dimension: One of 'query', 'page', 'country', 'device', 'date'.
    """
    svc, reason = _service()
    if svc is None:
        return {"status": "not_configured", "reason": reason}
    try:
        body = {"startDate": start_date, "endDate": end_date,
                "dimensions": [dimension], "rowLimit": 100}
        res = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = [
            {"key": r.get("keys", [None])[0], "clicks": r.get("clicks"),
             "impressions": r.get("impressions"), "ctr": r.get("ctr"),
             "position": r.get("position")}
            for r in res.get("rows", [])
        ]
        return {"status": "success", "dimension": dimension, "row_count": len(rows), "rows": rows}
    except Exception as e:
        return {"status": "unavailable", "reason": f"query failed: {e}"}


def _analyze_opportunities(rows: list[dict]) -> dict:
    """Turn raw query+page rows into a REAL, prioritized opportunity list. Pure function
    (testable): computes striking-distance and low-CTR opportunities from actual data."""
    totals = {
        "clicks": round(sum(r.get("clicks", 0) for r in rows)),
        "impressions": round(sum(r.get("impressions", 0) for r in rows)),
    }
    # Striking distance: ranking pos 5-20 with real impressions = one push from page 1.
    striking = sorted(
        (r for r in rows if 4.0 <= (r.get("position") or 99) <= 20.0
         and (r.get("impressions") or 0) >= 10),
        key=lambda r: r.get("impressions", 0), reverse=True)
    # Low CTR despite good position = title/meta rewrite opportunity.
    low_ctr = sorted(
        (r for r in rows if (r.get("position") or 99) <= 10.0
         and (r.get("impressions") or 0) >= 30 and (r.get("ctr") or 0) < 0.02),
        key=lambda r: r.get("impressions", 0), reverse=True)

    def slim(r):
        return {"query": r.get("query") or r.get("key"), "page": r.get("page"),
                "position": round(r.get("position", 0), 1),
                "impressions": round(r.get("impressions", 0)),
                "clicks": round(r.get("clicks", 0)), "ctr": round(r.get("ctr", 0), 4)}

    return {
        "status": "success", "totals": totals,
        "striking_distance": [slim(r) for r in striking[:15]],
        "low_ctr_opportunities": [slim(r) for r in low_ctr[:15]],
        "note": "Real Search Console data. Striking-distance = pos 5-20 with impressions "
                "(prioritize these). Low-CTR = good position, few clicks (rewrite title/meta).",
    }


def gsc_opportunities(site_url: str, days: int, tool_context: ToolContext) -> dict:
    """Pull REAL Search Console performance and rank the biggest SEO opportunities.

    This is how prioritization becomes real (not a proxy score): striking-distance
    keywords (pos 5-20) and low-CTR pages, from your actual rankings/clicks. Also stores
    a baseline in state for before/after. Needs a GSC service account.

    Args:
        site_url: The GSC property ('https://example.com/' or 'sc-domain:example.com').
        days: Look-back window in days (e.g. 28).
    """
    svc, reason = _service()
    if svc is None:
        return {"status": "not_configured", "reason": reason,
                "hint": "Add a GSC service account (GSC_SERVICE_ACCOUNT_FILE) as an owner of "
                "the property to prioritize by REAL rankings/clicks and measure before/after."}
    start, end = _daterange(days)
    try:
        body = {"startDate": start, "endDate": end, "dimensions": ["query", "page"],
                "rowLimit": 500}
        res = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = [{"query": r["keys"][0], "page": r["keys"][1], "clicks": r.get("clicks"),
                 "impressions": r.get("impressions"), "ctr": r.get("ctr"),
                 "position": r.get("position")} for r in res.get("rows", [])]
    except Exception as e:
        return {"status": "unavailable", "reason": f"query failed: {e}"}

    result = _analyze_opportunities(rows)
    result["window"] = {"start": start, "end": end, "days": days}
    if tool_context is not None:  # baseline for Phase-3 before/after
        tool_context.state["gsc_baseline"] = {"window": result["window"],
                                              "totals": result["totals"]}
    return result
