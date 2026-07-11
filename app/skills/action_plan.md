# Skill: Action Plan (Phase-1 close)

## Mission
Turn the analysis into a SPECIFIC, ready-to-implement plan the user can approve. This is
the last thing they see in Phase 1. Never generic — every action states the exact value.

## Format
1. **Summary (2-3 sentences):** what the site is (inferred niche), overall Health Score,
   top 2-3 opportunities.
2. **Action plan grouped by section** (Technical · On-Page · Content · Off-Page · AEO),
   weakest/highest-impact first. For each action give EXACT, ready-to-paste values.
3. **Closing ask (verbatim):** "Reply approve to implement the full plan, or tell me a
   section to focus on first (Technical / On-Page / Content / Off-Page / AEO)."

## Be THIS specific (good vs bad)
BAD (never do this): "Improve the homepage title and add a meta description."

GOOD (always do this):
> **On-Page · /  (homepage)** — Priority: High — Impact: On-Page +10, better CTR
> - **Title:** `Brain-Tech` → `AI Software & Web Development Company | Brain-Tech` (51 chars)
> - **Meta description (add, currently missing):** `Brain-Tech builds custom AI software,
>   web apps, and automation for growing businesses. Explore our services and start your
>   project today.` (149 chars)
> - **How:** content_optimizer drafts these exact values → you approve → written to
>   index.html `<title>` and a new `<meta name="description">`.

> **AEO · / ** — Priority: High — Impact: AEO +20 (eligible for AI citation)
> - **Add Organization JSON-LD** (currently none):
>   ```json
>   {"@context":"https://schema.org","@type":"Organization","name":"Brain-Tech",
>    "url":"https://brain-tech.net/","description":"AI software and web development"}
>   ```
> - **How:** inserted before `</head>`.

> **On-Page · link hygiene** — Priority: Med
> - Fix 4 generic anchors: change `read more` → `View our AI development services`, etc.
> - Add `alt` text to 2 image links: `<img alt="Brain-Tech portfolio">`.

## Rules
- Real values only: exact titles (~55 chars), exact ~155-char metas, actual JSON-LD blocks,
  the specific anchors/links to change. Ground copy/schema with retrieve_knowledge.
- Show `current → new` using the current values in the technical report. If a current value
  is genuinely unknown, say so and still give the exact proposed value.
- Cover top-priority items in full detail; list lower ones briefly. Don't implement anything.
