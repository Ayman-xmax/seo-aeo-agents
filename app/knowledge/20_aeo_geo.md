# AEO & GEO — Answer / Generative Engine Optimization (2025-2026)

Tier: synthesis (Princeton GEO paper + Ahrefs at-scale study are the most solid inputs)
Use: grounding for the serp_aeo, aeo_specialist, content_optimizer, strategy_synthesizer agents.

## What AEO is, vs SEO
Answer Engine Optimization structures content so AI systems understand, trust, and reproduce it
as a DIRECT ANSWER — rather than merely ranking a blue link. SEO optimizes for ranking positions;
AEO optimizes for being the answer (or a cited source inside a synthesized answer). Relationship
is additive, not competitive: SEO drives discoverability, AEO captures mindshare in zero-click /
conversational experiences. Strong traditional rankings are a PREREQUISITE for AEO. "Answer
engines": Google AI Overviews / AI Mode (formerly SGE), featured snippets & People Also Ask,
voice assistants, Perplexity, ChatGPT search, Gemini, Claude, Bing/Copilot.

## What GEO is, and the terminology reality
Generative Engine Optimization (GEO) was coined in the Princeton paper "GEO: Generative Engine
Optimization" (Aggarwal et al., arXiv 2311.09735, KDD 2024): optimizing content so generative
engines select, cite, and represent it favorably. Industry uses AEO, GEO, AIO, LLMO, and
SGE/AI-search optimization largely interchangeably. Where a line is drawn: AEO leans toward
"give a single direct answer" surfaces (featured snippets, voice, AI Overviews); GEO leans toward
"be favorably cited inside longer generated narratives" in chat LLMs. Practical guidance: treat
AEO and GEO as ONE discipline with two emphases; build shared primitives with per-surface tuning,
not separate pipelines.

## Optimization techniques — structure & direct answers
- Lead each key section with a 40-60 word direct answer that fully resolves the question before
  elaborating.
- Question-based headings (H2/H3 phrased as the actual user query).
- Extractable formatting: short paragraphs, bulleted/numbered lists, comparison tables, clear
  topic-boundary headers — reduces the work the model does to lift a passage.

## Optimization techniques — structured data & entities
- FAQPage schema on genuine visible Q&A blocks (high citation-rate format for LLMs even though
  Google dropped FAQ rich results).
- HowTo (steps), Article (headline, author, publish date, org), Organization, Service, Product.
- Build consistent entity identity: Organization schema, sameAs, Knowledge Graph presence,
  consistent NAP. Off-site brand mentions and citations in authoritative publications are the
  strongest correlating factor. E-E-A-T signals: named authors with bios/credentials, editorial
  standards, HTTPS, contact/privacy transparency.

## Optimization techniques — the Princeton-validated content levers
From the Princeton GEO experiment (GPT synthesizing answers over top-5 retrieved sources, ~10,000
queries, validated on Perplexity):
- WORKED (up to ~30-40% visibility gain): Cite Sources, add Quotations, add Statistics. Fluency
  Optimization (+15-30%), Authoritative Voice (+10-20%).
- Lower-ranked sites gained most from citing sources (up to +115%) — GEO can partly level the field.
- DID NOT WORK / HURT: keyword stuffing, "easy-to-understand" simplification, content padding,
  pure persuasion without evidence.

## Optimization techniques — chunking for LLM retrieval
Make passages retrievable in RAG: self-contained, semantically coherent chunks; each section
stands alone without external context. Research: moderate chunks (~1,800 chars) retrieve better;
overly large chunks (~14,400 chars) drop relevance 10-20%. Semantic/structural chunking beats
naive fixed-size. On-page translation: one idea per section, descriptive headers, front-loaded
answers → each section functions as a clean retrievable chunk.

## llms.txt — be honest about it
A proposed root-level `/llms.txt` file offering curated LLM-friendly content. Adoption is low and
effectiveness is UNPROVEN: ~0.3% of top-1,000 sites (June 2025); Google's Gary Illyes confirmed
Google does NOT support it and has no plans to; direct llms.txt fetches were negligible in
500M+ AI-bot-visit monitoring. Exception: developer-tool/IDE agents (Cursor, Claude Code,
Copilot, Windsurf) do fetch it for docs sites. Recommendation: generate it as a cheap, low-risk
OPTIONAL output — never present it as a primary ranking lever.

## How AI engines actually select & cite sources
Google AI Overviews (Ahrefs at scale): brand web mentions are the #1 correlating factor
(r ≈ 0.664); YouTube mentions correlate even higher (r ≈ 0.740, YouTube is the most-cited
domain). Traditional rankings gate everything — historically ~76% of cited URLs also rank top-10
(median position #2); some 2026 data shows AI Overviews increasingly citing beyond top-10, but
ranking still helps materially. Word count barely matters (r ≈ 0.04); intent-matching wins. URLs
ranking across multiple related fan-out sub-queries are 161% more likely to be cited.

## Per-platform citation behavior (differs significantly)
- Perplexity: multi-stage RAG (retrieves 5-10 candidates, cites ~3-4 after rerank through
  relevance/freshness/structure/authority/engagement); curated authority-domain boosts (GitHub,
  Reddit, LinkedIn, Amazon); cites the most sources of the three.
- ChatGPT: may answer with no citation; when citing, favors high-authority sources (Wikipedia-heavy).
- AI Overviews: RAG over Google's index — leans on ranking + brand authority.
- Only ~11% of domains are cited by BOTH ChatGPT and Perplexity → cross-platform coverage needs
  platform-specific tracking, not one score.

## Measuring AEO/GEO performance
Traffic/rank alone is insufficient. New KPIs:
- AI Share of Voice — % of AI answers in your category that mention your brand.
- Citation tracking — which URLs/domains get cited, on which platforms, for which prompts.
- Brand mention frequency & sentiment in LLM responses; prompt/topic coverage; competitive
  benchmarking.
Implementation: maintain a "prompt panel" — a set of category questions run on a schedule against
each engine, parsing responses for (a) brand mention, (b) your domain cited, (c) competitors
cited, (d) sentiment → share-of-voice + citation trend lines. LLM outputs are non-deterministic
and region-dependent — sample repeatedly and average.

## Practical AEO specialist workflow
1. Question/intent research — mine real questions (AlsoAsked, AnswerThePublic, PAA, LLM prompt
   logs); find which queries AI answers with competitor content.
2. Baseline audit — run the prompt panel: where are you cited/mentioned now vs competitors.
3. Content audit — does each section open with a direct answer? Q&A blocks? clean question-shaped
   headings? credible sourcing?
4. Optimize on-page — insert 40-60 word answer blocks, fix heading hierarchy, add statistics/
   quotes/citations (the Princeton levers), improve fluency.
5. Schema implementation & validation — FAQPage / HowTo / Article / Organization.
6. Authority & entity building — brand mentions, digital PR, YouTube presence, author credentials.
7. Pre-publish checklist — heading structure, direct-answer blocks, schema valid, freshness date,
   fact density.
8. Monitor & refresh — re-run prompt panel; featured-snippet wins appear in 2-4 weeks; AI-citation
   authority is a 3-6 month build.

## Relationship to the broader SEO workflow
Shared foundation AEO/GEO cannot skip: crawlability/indexability, site speed, HTTPS, clean IA,
and traditional rankings (RAG engines retrieve from search indexes — no traditional visibility →
no AI citation). What's distinct: optimizing for extraction and citation (answer-first structure,
chunk-friendly passages), off-page brand mentions and YouTube/third-party corpus presence weigh
more, new metrics (share of voice, citations, mentions), per-platform tuning, and statistics/
quotes/citations as empirically-validated content levers. Bottom line: AEO/GEO is an extension
layer ON TOP of an SEO pipeline, not a replacement. Reuse SEO primitives; add answer-block
generation, schema automation, chunk/structure scoring, entity/authority auditing, and a
multi-engine prompt-panel measurement service.

## Caveat on sourcing
Many secondary blogs cite very precise figures ("3.2× more likely", "r = 0.87") that trace to
vendor studies with undisclosed methodology — treat those as directional. The Princeton paper
and Ahrefs at-scale studies are the most methodologically solid inputs for agent scoring logic.
