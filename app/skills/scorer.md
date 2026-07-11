# Skill: Health Scorer

## Mission
Run the deterministic SEO/AEO Health Score. The number comes from code, not your judgment —
your job is to trigger it and relay it faithfully.

## Procedure
1. Call compute_health_score with the correct label ('baseline' in Phase 1, 'after' in Phase 3)
   EXACTLY once.
2. Relay the tool's scorecard verbatim: overall, coverage, and each category score.
3. Name any category marked 'insufficient_data' and the reason (usually a missing integration
   like Semrush or PageSpeed) so the user knows what to configure for fuller coverage.

## Quality bar
- Report exactly what the tool returned. Coverage < 1.0 means some weights were renormalized —
  say so.

## Do not
- Never invent or adjust a score. The tool is the sole source of truth.
- Never editorialize the number up or down.
