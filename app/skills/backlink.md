# Skill: Backlink & Authority Gap

## Mission
Profile the target's backlinks and find the highest-value link gaps vs competitors.

## Procedure
1. semrush_status. If configured: backlink_research on the target (referring domains, DR
   distribution, dofollow ratio, anchor profile, new vs lost), then the gap vs competitors
   (links ALL competitors have, dofollow only, min DR 50, min ~1,000 monthly traffic).
2. OWNED PATH (no paid API, no fee): crawl_links on the target + a few competitor/niche
   pages to build our link graph -> compute_authority (local PageRank) -> domain_authority
   (0-100, our own score) + referring_domains (backlinks we discovered). Same mechanism as
   DR/AS, computed locally. Coverage grows the more you crawl.
3. Also use retrieve_knowledge for a grounded authority/link-building STRATEGY (digital PR,
   unlinked-mention reclamation, brand mentions, HARO/Featured). Label strategy vs data.
4. Surface top opportunities and any toxic-link risks (for disavow) when data exists.

## Quality bar
- Authority scores (DR/DA/AS) reported as RELATIVE proxies, never ground truth; never
  compared across tools.
- Gaps ranked by (all-competitor overlap) × (relevance) × (achievable authority).

## Efficiency
- Focus on the intersect (links everyone but you has) — highest conversion, clearest pitch.
- Keep the list actionable (10-20 targets), not exhaustive.

## Do not
- Never invent referring domains or authority numbers.
- Never recommend buying links or manipulative schemes; paid links need rel=sponsored/nofollow.
