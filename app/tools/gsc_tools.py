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

import os

_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


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
