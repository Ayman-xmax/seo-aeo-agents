# Skill: Post-Change Verifier

## Mission
Prove the changes are actually live and correct by re-crawling — never assume an edit worked.
Your re-crawl also refreshes the signals the 'after' score is computed from.

## Procedure
1. Read state['change_log'] to get the changed URLs.
2. For each changed URL: audit_technical_basics + audit_links again; check_robots_and_sitemap
   once for the site; get_crux to refresh Core Web Vitals.
3. Compare each change_log item to the live page:
   - Title/meta/heading edits reflected? Schema present? Links fixed?
4. Mark each item verified / unverified / regressed, with the tool evidence.

## Quality bar
- Every verdict backed by a fresh tool result, not the change_log's stated intent.
- Regressions (something that got worse) flagged loudly.

## Efficiency
- Only re-crawl the pages that changed, plus any they link to that were affected.
- Run the same page's basics + links back-to-back so signals harvest cleanly.

## Do not
- Never assume a change is live. Never modify the site.
