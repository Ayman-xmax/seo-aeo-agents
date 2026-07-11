# Skill: Competitor Discovery

## Mission
Find the site's TRUE SEO competitors (domains competing for the same organic keywords),
then READ what they do well — their topics, keywords, and content approach — so the
strategy can learn from them. Include any competitor URLs the user provided.

## Procedure
1. OWNED FREE PATH: call seed_index with 3-5 head queries → builds our SERP index; then
   organic_competitors → reads the domains that recur most = your SEO competitors. The
   index compounds every run (our owned asset). Needs SEARXNG_URL (self-hosted, free).
2. If Semrush is configured, also use organic_research / overview_research for keyword-
   overlap confirmation.
3. Rank by frequency/overlap; keep the top 3-5, each with the queries that surfaced it.
4. If SEARXNG_URL is unset and Semrush is off, call semrush_status and report exactly
   what's missing — do not guess domains.

## Quality bar
- 3-5 competitors max (more dilutes the gap analyses downstream).
- Each competitor carries the overlap metric that justifies it.
- Distinguish SEO competitors from any business rivals the user named that DON'T overlap.

## Efficiency
- One or two well-scoped Semrush calls beat many broad ones (respect API cost).
- Hand a clean competitor list downstream — keyword & backlink agents reuse it for gaps.

## Do not
- Never invent competitor domains or overlap numbers.
- Don't analyze their on-page/technical details (other agents own that).
