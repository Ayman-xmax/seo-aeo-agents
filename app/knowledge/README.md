# Knowledge Corpus (RAG Layer 2)

Drop curated, authoritative SEO/AEO source documents here as `.md` / `.txt`, then run:

```bash
uv run python -m app.knowledge_base.ingest
```

This is **best-practice knowledge only** — the qualitative playbook the agents reason
over and cite. It is deliberately **separate** from:

- **Deterministic rules** (`app/config.py`) — exact thresholds/quotas live in code, never here.
- **Live data** (Semrush MCP + Google APIs) — real-time metrics, never here.

## Rules for what belongs here
- Prefer official sources: Google Search Central, web.dev, Chrome docs.
- Record provenance in `versions.yaml` and keep `last_updated` current.
- Remove or update docs when Google changes a rule (e.g. FAQ/HowTo rich-result deprecation).
- Keep each doc focused; the ingester chunks by heading (~1800 chars).

The `00_google_crawlable_links.md` doc is seeded from the page you provided as the
worked example. Add the SEO-process and AEO/GEO syntheses next (`10_*`, `20_*`).
