# The Modern SEO Process (2025-2026)

Tier: synthesis (cross-verified against Google Search Central, web.dev, Ahrefs, Semrush, Backlinko)
Use: grounding for the technical_audit, keyword_research, backlink, strategy_synthesizer agents.

## SEO lifecycle — a repeating cycle, not a one-shot project
Run SEO in focused 30-90 day sprints. Canonical phase order:
1. Discovery & Technical Audit — establish a baseline before changing anything.
2. Strategy & Research — keyword research + mapping, fix prioritization, content-gap analysis.
3. Technical Implementation — crawl/index, sitemaps, canonicals, robots, architecture, Core Web Vitals, schema.
4. On-Page Optimization — titles, metas, headings, keyword targeting, internal links.
5. Content Creation — cluster → brief → draft → publish, matched to intent.
6. Off-Page / Link Building — backlinks, digital PR, brand mentions.
7. Monitor, Report & Iterate — rank tracking, GSC/GA4 analytics, feed back into the next cycle.

## Technical SEO — crawlability
Verify Googlebot by reverse-DNS to googlebot.com/google.com, not the spoofable user-agent.
Key tokens: Googlebot (smartphone, mobile-first default), Googlebot-Image/Video/News,
Google-InspectionTool, GoogleOther, Google-Extended (controls Gemini/Vertex training — does
NOT affect Search). Crawl budget only matters materially at 1M+ pages changing weekly, 10k+
changing daily, or many URLs stuck in "Discovered – currently not indexed." Budget wasters:
duplicate content, faceted-nav/parameter explosion, soft 404s, redirect chains, infinite
spaces. Google does not honor crawl-delay.

## Technical SEO — indexing
Pipeline: Discovery → Crawl → Render → Index. `noindex` (meta tag or X-Robots-Tag header) is
the only reliable exclusion. CRITICAL: a noindex page must NOT be blocked in robots.txt — if
blocked, Googlebot never sees the directive and the URL can still be indexed. Two GSC
non-indexed states to differentiate: "Discovered – currently not indexed" (crawl deprioritized,
often perceived thin/low quality) vs "Crawled – currently not indexed" (crawled but rejected:
duplication, low quality, weak internal linking). Fixes: raise uniqueness/quality, strengthen
internal links, de-orphan pages.

## Technical SEO — XML sitemaps
Hard limits: ≤50,000 URLs AND ≤50 MB uncompressed per file; exceed either → split with a
sitemap index file. UTF-8, entity-escaped, absolute URLs. `<lastmod>` only if consistently
accurate (don't fake it). `<priority>` and `<changefreq>` are IGNORED by Google — don't emit
them. Include only canonical, indexable, 200-status URLs.

## Technical SEO — robots.txt
Root-hosted per host+protocol+port; ≤500 KiB (rest ignored); cached ≤24h. Only four directives:
user-agent, disallow, allow, sitemap. crawl-delay unsupported. Wildcards `*` and `$`; field
names case-insensitive, paths case-sensitive; conflict resolution = most specific by path
length, ties → least restrictive wins. Controls crawling, NOT indexing — never combine
Disallow + noindex.

## Technical SEO — Core Web Vitals
Pass = all three at the 75th percentile of FIELD data (mobile + desktop separately).
- LCP (loading): good ≤2.5s, poor >4.0s.
- INP (interactivity): good ≤200ms, poor >500ms. INP replaced FID on 2024-03-12; it measures
  latency of ALL interactions, not just the first.
- CLS (visual stability): good ≤0.1, poor >0.25.
Field data (CrUX) is what Google uses to rank; lab data (Lighthouse) cannot measure INP well —
never report lab INP as authoritative. Only ~54.6% of sites pass all three, so passing is a
real edge.

## Technical SEO — mobile-first & structured data
Mobile-first indexing has been 100% complete since 2024-07-05 — Google indexes/ranks the
mobile version. Audit for content parity (same primary content, headings, structured data,
metadata on mobile). Structured data: use JSON-LD in the rendered DOM; markup must match
visible content. DEPRECATED: HowTo rich results fully removed (Sept 2023); FAQ rich results
effectively dead (restricted then dropped) — FAQPage is still parsed for entity comprehension
but yields no SERP feature. Types still producing rich results: Article, Breadcrumb, Product,
Review/AggregateRating, Recipe, Video, Organization, LocalBusiness, Event, JobPosting, Course,
Dataset, SoftwareApp.

## Technical SEO — canonicalization
Signal strength: 301/308 redirect > rel=canonical (in <head> or Link header) > sitemap
inclusion. Best practice: self-referential canonical, absolute URLs, one per page, consistent
internal linking, prefer HTTPS. Audit for: canonical pointing to a redirected/noindex/404/
blocked URL, relative canonical URLs, conflicting tags, canonical in <body>, fragment (#)
canonicals.

## On-page — keyword research, clustering, mapping
Seed → expand (Ahrefs Keywords Explorer, Semrush Keyword Magic, Google Keyword Planner) →
evaluate volume, Keyword Difficulty, CPC, SERP features → filter for winnability (beginners cap
KD ≤30). Ahrefs KD is computed from the number of unique referring domains to the current
top-10. Clustering = grouping keywords by shared intent/semantics/SERP overlap; mapping =
assigning each cluster to one URL to prevent cannibalization. Reliable method combines intent +
semantic meaning + SERP similarity (compare top-10 overlap). Highest-volume/clearest term = the
page's primary keyword; supporting terms → subheadings/FAQ.

## On-page — titles, metas, headings
Titles: measure PIXELS, not chars. Optimal 50-60 chars ≈ 575-600px desktop; hard cap ~600px.
51-55 chars have the lowest rewrite rate; >70 chars → ~100% rewritten; highest traffic at
55-60 chars. Google rewrote ~76% of titles in Q1 2025 — front-load the primary keyword, keep
unique. Meta descriptions: 150-160 chars (≈920px); key message in the first ~120 chars for
mobile; not a ranking factor but drives CTR. Headings: exactly one H1; logical hierarchy, no
skipped levels; descriptive; primary keyword in H1, secondary in H2/H3. Clean structure drives
AI Overview / featured-snippet / PAA eligibility.

## On-page — internal linking & content
Internal links: descriptive, varied anchor text (avoid "click here"); ~2-5 contextual links
per 1,000 words; <150 links/page; important pages ≤3 clicks from homepage; pillar-cluster
pyramid; links must be crawlable <a href>. Content: match search intent first (compare against
the current top 10). TF-IDF is a first filter, not the judge; shift from keyword density to
topic comprehensiveness. E-E-A-T (Experience, Expertise, Authoritativeness, Trust — Trust is
most important) is NOT a direct ranking factor but a framework Google's systems approximate.
Automatable proxies: first-hand media/data, credentials/depth, authoritative backlinks/mentions,
bylines + author schema + sourcing + dates + HTTPS. Use Google's Who/How/Why self-assessment.

## Off-page — backlinks & authority
Quality-backlink factors: (1) authority of the referring page (not just domain; fewer outbound
links = more equity); (2) relevance (most-emphasized modern factor); (3) anchor text —
descriptive but naturally varied (over-optimized exact-match = spam signal); (4) dofollow (only
dofollow reliably passes equity); (5) editorial in-content placement. Authority metrics (DR/DA/
Authority Score) are ALL third-party, none are Google, 0-100 logarithmic — never compare across
tools (~30%+ deviation); use as relative filters only. Google's stance: links are declining —
Gary Illyes says links are "not in the top 3" factors; Penguin now neutralizes/ignores spammy
links rather than penalizing. Paid links must carry rel="sponsored" or "nofollow". Rising
concept: brand mentions / entity presence over raw link counts.

## Content strategy — clusters, gaps, intent
Topic clusters (hub-and-spoke): one pillar page (broad) + N cluster pages (one subtopic each);
pillar links to every cluster, every cluster links back. Builds topical authority, prevents
cannibalization. Content-gap analysis: competitor ranking keywords minus yours (input domain +
up to 4 competitors → filter by position, difficulty, "Missing" bucket → prioritize by traffic
× relevance × achievable difficulty). Search intent — four types, classify via keyword
heuristics THEN mandatory SERP analysis (the dominant page-1 format defines required intent):
Informational (how/what/guide → blog/pillar), Navigational (brand/login → homepage),
Commercial (best/top/review/vs → listicle/comparison), Transactional (buy/price/near me →
product/pricing).

## Competitor analysis
Identify competitors empirically from keyword overlap (Ahrefs "Organic Competitors" / Semrush
"Competitors"), not from a user list — SEO competitors ≠ business competitors. Cap at 3-5;
refresh quarterly. Keyword-gap states (Semrush): Missing (all rivals rank, you don't — highest
value), Weak (you rank worse — easiest wins), Shared/Strong/Untapped. Backlink gap / link
intersect: default quality filters = links to all competitors + dofollow only + min DR 50 +
min 1,000 monthly domain traffic. SERP analysis: the SERP is no longer 10 blue links — classify
features. 2025 prevalence (volatile): AI Overviews ~15-27%, PAA ~79-90%, sitelinks ~85%,
featured snippets collapsing ~5.5%. AIOs correlate with ~58% CTR reduction for the top result —
discount traffic potential when an AIO is present.

## Google tooling & APIs (automation-critical)
- GSC Search Analytics: 25,000 rows/call, 1,200 QPM/site, 16-month rolling history (warehouse
  older data yourself); data is sampled.
- GSC URL Inspection: 2,000/day/site (the tightest bulk-check constraint); returns verdict,
  coverageState, googleCanonical vs userCanonical, lastCrawlTime. This is the way to answer
  "is this URL indexed?"
- Indexing API: officially JobPosting/BroadcastEvent ONLY, 200 publish/day. Pushing arbitrary
  URLs is unsupported/abuse-risk. For general pages use sitemaps for discovery + URL Inspection
  to verify.
- GA4 Data API: segment organic via sessionDefaultChannelGroup = "Organic Search"; never mix
  user-scoped dimensions with session/event metrics.
- PageSpeed / CrUX: use CrUX for cheap real-user field CWV (28-day rolling lag), Lighthouse/PSI
  for lab diagnostics on flagged pages.

## What "indexing" vs "ranking" vs "reranking" actually mean
Official 3-stage model: Crawling → Indexing → Serving/Ranking. Indexing ≠ ranking (necessary
but not sufficient). Finer model: Retrieval (candidate set + initial score) → Reranking
(twiddlers: freshness, quality, diversity boosts/demotions). Leaked/testimony components
(NavBoost click reranker, Glue, Mustang scoring, RankBrain, DeepRank) are hypotheses for what
to optimize, NOT queryable signals. Design implication: you can only measure the observable ends
— crawl/index status (URL Inspection, GSC coverage) and ranking outcomes (position, impressions,
clicks, GA4 sessions). Optimize genuine satisfying engagement + E-E-A-T proxies; never try to
game the reranker (it is not controllable).

## Key metrics / KPIs
GSC: impressions (leading indicator), clicks, CTR, avg position. CTR by position (Backlinko):
Pos 1 ≈ 27.6%, Pos 2 ≈ 18.7%, Pos 3 ≈ 10.2%; top 3 ≈ 54% of clicks. Share of Voice = Σ your
ranking-keyword traffic ÷ Σ total available traffic across the keyword set. Backlinks: referring
domains (weight over raw count), link velocity (net referring-domain change, 30-day rolling).
Technical: index coverage, crawl errors, CWV pass rate. GA4: engaged session = ≥10s OR ≥2
pageviews OR ≥1 conversion. ROI timeline: ~0.8x at 6mo, ~2.6x at 12mo, ~3.8x at 18mo. Emerging
AEO metrics: AI Citation Rate, AI Mention Rate, AI Share of Voice.
