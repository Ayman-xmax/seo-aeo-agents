# Skill: Strategy Synthesis

## Mission
Turn the five collector reports into plain-language conclusions and a prioritized,
grounded roadmap with content briefs. This is the "conclude + strategize" stage.

## Procedure
1. Read competitor_report, tech_report, keyword_report, backlink_report, serp_report.
2. For anything you'll recommend, retrieve_knowledge to ground it and cite the source doc.
3. Write findings — each references the report/field it came from (evidence).
4. Build the roadmap: order by (impact × ease), quick wins first. Tie each item to a finding.
5. Draft content briefs for the top content opportunities (primary/secondary keywords,
   intent, outline, PAA, AEO answer blocks, internal-link targets).
6. List every check that couldn't run under unavailable_data — honestly.

## Quality bar / output shape
Output JSON matching StrategyRoadmap: summary, findings[], roadmap[] (priority-ordered),
content_briefs[], unavailable_data[]. No finding without a supporting report or knowledge
passage.

## Efficiency
- Prioritize ruthlessly — a 10-item roadmap that ships beats a 50-item wish list.
- Group related fixes (e.g. all canonical issues) into one roadmap item.
- Lead the summary with the 3 things that matter most.

## Do not
- Never introduce findings not supported by data. Never recommend against-guidelines tactics.
- Never modify the site.
