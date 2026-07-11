# Skill: Competitor Discovery

## Mission
Find the site's TRUE SEO competitors (domains competing for the same organic keywords),
not the user's business rivals.

## Procedure
1. Call semrush_status first. If not_configured, report exactly what env vars are missing
   and return an empty list — do not guess.
2. Use organic_research / overview_research to find domains with high keyword overlap for
   the niche and target URL.
3. Rank by keyword-overlap %; keep the top 3-5. Note each competitor's overlap evidence.

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
