# Skill: Technical + On-Page Audit

## Mission
Produce a ground-truth technical/on-page audit of the site's key pages. Every issue
must cite the exact tool field it came from.

## Procedure (tool order)
1. check_robots_and_sitemap(url) ONCE for the site — get declared sitemaps, robots size.
2. For each key page (homepage + 3-8 important URLs from the brief):
   a. audit_technical_basics(url) — title/meta length, single H1, canonical, meta-robots,
      JSON-LD types (flag deprecated FAQ/HowTo).
   b. audit_links(url) — apply Google's crawlable-link rules literally.
3. get_crux(url) for field Core Web Vitals; run_pagespeed(url, 'mobile') for lab diagnostics
   on any page CrUX can't cover. Mobile first — Google indexes the mobile version.
4. inspect_url(page_url, site_url) to confirm index status where a GSC property is configured.

## Quality bar / checklist
- Title present, ~50-60 chars (pixel proxy); exactly one H1; canonical absolute & self-ref.
- CWV reported from FIELD data (CrUX); never report lab INP as authoritative.
- Link issues classified: non-anchor href, onclick-only, javascript:, generic/stuffed anchor,
  missing alt/title, chained links, >150 links/page.
- robots.txt <=500 KiB; sitemap declared; never Disallow + noindex on the same area.

## Efficiency
- Cap at the pages that matter; don't crawl the whole site in Phase 1.
- Batch per-page: basics + links back-to-back so signals harvest together.
- The scoring engine reads your tool outputs automatically — call the tools, don't
  re-summarize numbers you didn't get from them.

## Do not
- Never estimate CWV, page counts, or index status. Missing data = 'unavailable'.
- Don't recommend content/keyword strategy or modify the site.
