# Skill: Competitor Discovery

## Mission
Find the site's TRUE SEO competitors (domains competing for the same organic keywords),
not the user's business rivals.

## Procedure
1. FREE PATH: run serp_competitors on 3-5 head queries from the niche; aggregate the
   domains that recur across queries — those are your SEO competitors. (Needs DataForSEO
   creds; cheap pay-per-call, no Semrush subscription.)
2. If Semrush is configured, also use organic_research / overview_research for keyword-
   overlap confirmation.
3. Rank by frequency/overlap; keep the top 3-5, each with the queries that surfaced it.
4. If neither serp_competitors nor Semrush is configured, call semrush_status and report
   exactly what's missing — do not guess domains.

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
