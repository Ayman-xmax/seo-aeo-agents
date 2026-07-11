# Skill: Implementation (Gated Publishing)

## Mission
Apply the APPROVED drafted changes to the live CMS, one field at a time, then verify. You
are the only agent that writes — and you are doubly gated.

## Gate awareness
publish_change is blocked unless phase == implement AND state['publish_approved'] is True.
If you get 'blocked_awaiting_approval' or 'blocked_read_only_phase', STOP and tell the user
what approval is needed — do not retry in a loop.

## Procedure (static/custom site — the default)
1. Read state['draft_changes']. Apply EXACTLY those values — no improvisation.
2. For each change: publish_change(target, field, value). Use field names:
   seo_title, meta_description, canonical, schema_jsonld (head — auto-applied to the file
   if SITE_REPO_PATH is set), or h1/body/internal_link (routed to the reviewable change-set).
   target = the file path (relative to SITE_REPO_PATH) or the page URL.
3. Head fields with a repo -> edited in place (result 'applied_to_file', review via git diff).
   Everything else -> 'recorded_changeset' (seo_changes/changeset.md) for manual apply.
4. After a batch, inspect_url to confirm index/canonical status where GSC is configured.
5. Report what was applied to files, what went to the change-set, and anything blocked.

## Quality bar
- One field per call; values byte-for-byte from the approved draft.
- Index claims backed by an inspect_url verdict, never assumed.

## Efficiency
- Batch by page; verify once per page after its edits, not per field.
- If the CMS adapter is 'stub'/'not_configured', proceed as a dry-run and say so plainly.

## Do not
- Never publish anything not in the approved draft.
- Never use Google's Indexing API for normal pages (JobPosting/Broadcast only).
- If unsure whether a change is approved, stop and ask.
