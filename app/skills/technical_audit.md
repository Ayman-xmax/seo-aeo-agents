# Skill: Technical + On-Page Audit

## Mission
Produce a ground-truth technical/on-page audit of the site's key pages. Every issue
must cite the exact tool field it came from.

## Procedure (tool order)
1. audit_site(target_url) ONCE — inventories + audits the WHOLE site (every page:
   title/meta/H1/canonical/schema, link hygiene, content depth) and feeds the site-wide
   score. This is the main step. Report the summary + the specific pages with issues.
2. check_robots_and_sitemap(url) ONCE — declared sitemaps, robots size.
3. run_lighthouse(homepage, 'mobile') — Core Web Vitals (local, no key).
4. Follow-up on a single page only if it needs detail: audit_technical_basics / audit_links
   / audit_content.
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
