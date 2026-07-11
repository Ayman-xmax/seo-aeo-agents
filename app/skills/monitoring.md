# Skill: Monitoring & Ongoing Tracking

## Mission
Report current organic performance from real telemetry and set up the recurring tracking that
closes the loop into the next cycle.

## Procedure
1. Pull what's configured:
   - search_analytics(site, start, end, dimension) — clicks/impressions/CTR/position (16-mo history).
   - query_organic(start, end) — GA4 organic sessions/engagement/conversions.
   - get_crux(url) — field Core Web Vitals trend.
   - inspect_url — spot-check index status of key pages.
2. For every source with no creds, report 'not_configured' and what to set — do not guess.
3. Recommend cadence: re-audit interval + the AEO prompt-panel schedule for AI share-of-voice.

## Quality bar
- Every metric is tool-returned; unavailable sources named explicitly.
- Distinguish leading indicators (impressions) from lagging ones (conversions).

## Efficiency
- Pull a compact, decision-useful set (top queries/pages), not every row.
- Respect quotas: URL Inspection is 2,000/day/site — spot-check, don't bulk-scan.

## Do not
- Never fabricate rankings, sessions, or citation metrics.
