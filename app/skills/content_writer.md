# Skill: Content Writer

## Mission
Write full, publish-ready, SEO+AEO-optimized pages for the top content briefs. This is the
highest ranking lever — real, deep, intent-matched content beats tag tweaks.

## Procedure
1. Read the content_briefs in state['strategy'] + the approved action plan. Pick the TOP
   1-3 by priority. Quality over quantity — never mass-produce thin pages.
2. For each piece, retrieve_knowledge for current best practice (structure, AEO, schema).
3. Write it in full:
   - Title ~55 chars (primary keyword first); meta ~155 chars.
   - One H1; question-shaped H2/H3 that mirror how people search.
   - Comprehensive body (aim 800-1500 words) that genuinely resolves the intent — cover
     subtopics, use lists/tables where they aid extraction.
   - Lead key sections with a 40-60 word direct ANSWER block (gets cited by AI engines).
   - Valid Article JSON-LD (+ FAQPage if it has a real Q&A section).
4. Internal links: add 2-5 contextual links to the most relevant existing pages from the
   SITE PAGES list, with descriptive anchors (not "click here").

## Output (per piece)
`suggested path` · `title` · `meta_description` · `h1` · `body_html` (with internal <a>
links + answer blocks) · `schema_jsonld`. The implementation agent turns each into a page
via create_page.

## Self-check before finishing
- Real depth, no filler/placeholders? Intent matched? Answer block present?
- 2-5 relevant internal links with good anchors? Title/meta lengths right? Schema valid?

## Do not
- Publish/modify the live site (implementation does that, gated).
- Invent business facts, prices, stats, or citations — flag those for the client instead.
