# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Google Analytics 4 Data API — organic-search engagement metrics.

Degrades to `not_configured` when creds/libs are absent (no guessing). Needs a
service account with GA4 read access; property id in GA4_PROPERTY_ID and key in
GA4_SERVICE_ACCOUNT_FILE.
"""

from __future__ import annotations

import os


def query_organic(start_date: str, end_date: str) -> dict:
    """Pull organic-search sessions & engagement from GA4 for a date range.

    Args:
        start_date: ISO 'YYYY-MM-DD' or GA4 relative like '28daysAgo'.
        end_date: ISO 'YYYY-MM-DD' or 'today'.
    """
    prop = os.environ.get("GA4_PROPERTY_ID")
    key_file = os.environ.get("GA4_SERVICE_ACCOUNT_FILE")
    if not prop or not key_file or not os.path.exists(key_file):
        return {"status": "not_configured",
                "reason": "Set GA4_PROPERTY_ID and GA4_SERVICE_ACCOUNT_FILE."}
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient  # type: ignore
        from google.analytics.data_v1beta.types import (  # type: ignore
            DateRange,
            Dimension,
            Filter,
            FilterExpression,
            Metric,
            RunReportRequest,
        )
        from google.oauth2 import service_account  # type: ignore
    except Exception:
        return {"status": "not_configured",
                "reason": "google-analytics-data not installed (add it to run GA4 live)."}
    try:
        creds = service_account.Credentials.from_service_account_file(key_file)
        client = BetaAnalyticsDataClient(credentials=creds)
        req = RunReportRequest(
            property=f"properties/{prop}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name="sessions"), Metric(name="engagedSessions"),
                     Metric(name="engagementRate"), Metric(name="conversions")],
            dimension_filter=FilterExpression(filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search"))),
        )
        resp = client.run_report(req)
        rows = [{"metrics": [v.value for v in row.metric_values]} for row in resp.rows]
        return {"status": "success", "metric_headers":
                ["sessions", "engagedSessions", "engagementRate", "conversions"],
                "rows": rows}
    except Exception as e:
        return {"status": "unavailable", "reason": f"GA4 query failed: {e}"}
