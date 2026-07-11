# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""FastMCP server: FREE SEO data (replaces Semrush's keyword role at $0).

Tools exposed to the agents:
  - autocomplete       : Google Suggest completions (free, no key)
  - keyword_ideas      : seed -> large real-query list via alphabet expansion
  - question_keywords  : question-form keywords (how/what/why/best/vs ...)
  - serp_competitors   : top-ranking domains for a query (OPTIONAL, DataForSEO pay-
                         per-call — far cheaper than a Semrush subscription; returns
                         not_configured without credentials)

Honesty guarantee: these tools return REAL suggestions. They do NOT invent search
volumes or difficulty scores — that data genuinely requires a paid index, so we
omit it rather than fake it.

Run:  python -m seo_data_mcp.server   (stdio transport)
"""

from __future__ import annotations

import os
from statistics import mean
from urllib.parse import urlparse

import requests
from mcp.server.fastmcp import FastMCP

from . import store

mcp = FastMCP("seo-data")


def _domain_of(url: str) -> str:
    net = urlparse(url).netloc.lower()
    return net[4:] if net.startswith("www.") else net

_UA = "Mozilla/5.0 (compatible; SEO-AEO-Agent/1.0)"
_SUGGEST = "https://suggestqueries.google.com/complete/search"
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_QUESTION_PREFIXES = [
    "how to", "what is", "why", "when", "where", "which", "who",
    "best", "top", "is", "can", "does", "vs", "alternative to", "cheap",
]


def _suggest(query: str, market: str) -> list[str]:
    """Call Google Suggest (client=firefox returns JSON). Returns [] on failure."""
    try:
        r = requests.get(
            _SUGGEST,
            params={"client": "firefox", "hl": "en", "gl": market, "q": query},
            headers={"User-Agent": _UA},
            timeout=8,
        )
        data = r.json()
        return list(data[1]) if isinstance(data, list) and len(data) > 1 else []
    except Exception:
        return []


@mcp.tool()
def autocomplete(query: str, market: str = "us") -> dict:
    """Real Google Autocomplete suggestions for a query (free, no API key).

    Args:
        query: The seed query.
        market: Two-letter country code (e.g. 'us', 'gb', 'in').
    """
    sugg = _suggest(query, market)
    return {"status": "success", "query": query, "market": market,
            "count": len(sugg), "suggestions": sugg}


@mcp.tool()
def keyword_ideas(seed: str, market: str = "us") -> dict:
    """Expand a seed keyword into a large list of REAL search queries.

    Uses alphabet-suffix autocomplete expansion. Returns actual user queries — NOT
    search volumes (those need a paid index and are intentionally omitted).

    Args:
        seed: The seed keyword/topic.
        market: Two-letter country code.
    """
    ideas: set[str] = set(_suggest(seed, market))
    for ch in _ALPHABET:
        ideas.update(_suggest(f"{seed} {ch}", market))
    ideas.discard(seed)
    ordered = sorted(ideas)
    store.upsert_keywords(ordered, market, source="autocomplete")  # accumulate = ownership
    return {"status": "success", "seed": seed, "market": market,
            "count": len(ordered), "keywords": ordered,
            "note": "Real autocomplete queries, saved to our owned index. Volume needs "
            "Google Ads Keyword Planner; difficulty via keyword_difficulty."}


@mcp.tool()
def question_keywords(seed: str, market: str = "us") -> dict:
    """Generate question-form keywords for a topic (great for AEO answer targets).

    Args:
        seed: The seed keyword/topic.
        market: Two-letter country code.
    """
    out: set[str] = set()
    for prefix in _QUESTION_PREFIXES:
        for s in _suggest(f"{prefix} {seed}", market):
            out.add(s)
    ordered = sorted(out)
    return {"status": "success", "seed": seed, "market": market,
            "count": len(ordered), "questions": ordered}


@mcp.tool()
def serp_competitors(query: str, market: str = "us") -> dict:
    """Top organic domains ranking for a query (OPTIONAL, via DataForSEO).

    Pay-per-call and far cheaper than a Semrush subscription. Returns
    not_configured (never guesses) unless DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD
    are set.

    Args:
        query: The search query.
        market: Two-letter country code.
    """
    login = os.environ.get("DATAFORSEO_LOGIN")
    pwd = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not pwd:
        return {"status": "not_configured",
                "reason": "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD for paid SERP "
                "data, or rely on the serp_aeo agent's google_search for competitors."}
    try:
        loc = {"us": 2840, "gb": 2826, "in": 2356, "ca": 2124, "au": 2036}.get(market, 2840)
        payload = [{"keyword": query, "location_code": loc, "language_code": "en",
                    "depth": 10}]
        r = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/live/regular",
            json=payload, auth=(login, pwd), timeout=30,
        )
        data = r.json()
        items = (((data.get("tasks") or [{}])[0].get("result") or [{}])[0]
                 .get("items") or [])
        domains = []
        for it in items:
            if it.get("type") == "organic" and it.get("domain"):
                domains.append({"rank": it.get("rank_group"), "domain": it["domain"],
                                "url": it.get("url")})
        return {"status": "success", "query": query, "top_domains": domains[:10]}
    except Exception as e:
        return {"status": "unavailable", "reason": f"DataForSEO call failed: {e}"}


@mcp.tool()
def domain_authority(domain: str) -> dict:
    """Domain authority for a domain (FREE, Open PageRank — Common-Crawl based).

    0-10 score + global rank, cached in our owned index. This is our free stand-in
    for Semrush/Ahrefs authority. Set OPENPAGERANK_API_KEY (free) to enable.

    Args:
        domain: Bare domain, e.g. 'example.com'.
    """
    key = os.environ.get("OPENPAGERANK_API_KEY")
    if not key:
        return {"status": "not_configured",
                "reason": "Set OPENPAGERANK_API_KEY (free at openpagerank.com) to enable "
                "authority scores without a paid tool."}
    try:
        r = requests.get("https://openpagerank.com/api/v1.0/getPageRank",
                         params=[("domains[]", domain)], headers={"API-OPR": key},
                         timeout=15)
        item = (r.json().get("response") or [{}])[0]
        score = item.get("page_rank_decimal")
        rank = item.get("rank")
        if score is None:
            return {"status": "unavailable", "domain": domain,
                    "reason": "No authority data for this domain."}
        store.upsert_authority(domain, float(score), int(rank or 0))
        return {"status": "success", "domain": domain, "authority_0_10": score,
                "global_rank": rank, "source": "open_pagerank"}
    except Exception as e:
        return {"status": "unavailable", "reason": f"Open PageRank call failed: {e}"}


@mcp.tool()
def serp_lookup(query: str, market: str = "us") -> dict:
    """Top organic domains for a query via self-hosted SearXNG (FREE, owned).

    Results are saved to our SERP index, which powers competitor discovery and
    keyword difficulty. Set SEARXNG_URL to your SearXNG instance (self-host = $0,
    fully owned). Returns not_configured otherwise (never guesses).

    Args:
        query: The search query.
        market: Two-letter country/language code.
    """
    base = os.environ.get("SEARXNG_URL")
    if not base:
        return {"status": "not_configured",
                "reason": "Set SEARXNG_URL to a SearXNG instance (self-host for free, "
                "full ownership) to enable SERP/competitor/difficulty data."}
    try:
        r = requests.get(f"{base.rstrip('/')}/search",
                         params={"q": query, "format": "json", "language": market},
                         timeout=20)
        results = r.json().get("results", [])
        rows = []
        for i, x in enumerate(results[:10]):
            if x.get("url"):
                rows.append({"rank": i + 1, "domain": _domain_of(x["url"]),
                             "url": x["url"]})
        store.record_serp(query, market, rows)  # accumulate = ownership
        return {"status": "success", "query": query, "count": len(rows), "rows": rows}
    except Exception as e:
        return {"status": "unavailable", "reason": f"SearXNG query failed: {e}"}


@mcp.tool()
def keyword_difficulty(keyword: str, market: str = "us") -> dict:
    """OUR OWN keyword difficulty (0-100) — we compute it, we own the formula.

    Fetches the top-10 SERP (serp_lookup) and averages the ranking domains' Open
    PageRank authority: stronger incumbents => harder. Requires SEARXNG_URL and
    OPENPAGERANK_API_KEY (both free). Honest: this is our approximation, not Semrush's.

    Args:
        keyword: The keyword to score.
        market: Two-letter country/language code.
    """
    serp = serp_lookup(keyword, market)
    if serp.get("status") != "success" or not serp.get("rows"):
        return {"status": "needs_serp_source",
                "reason": "keyword_difficulty needs SERP data — configure SEARXNG_URL."}
    scores = []
    for row in serp["rows"]:
        a = domain_authority(row["domain"])
        if a.get("status") == "success" and a.get("authority_0_10") is not None:
            scores.append(float(a["authority_0_10"]))
    if not scores:
        return {"status": "needs_authority",
                "reason": "keyword_difficulty needs OPENPAGERANK_API_KEY for authority."}
    kd = round(mean(scores) / 10 * 100)
    return {"status": "success", "keyword": keyword, "difficulty_0_100": kd,
            "sampled_domains": len(scores),
            "basis": "mean Open PageRank of top-10 ranking domains (our own formula)"}


@mcp.tool()
def organic_competitors(market: str = "us", limit: int = 5) -> dict:
    """SEO competitors from OUR accumulated SERP index (FREE, owned, grows over time).

    The more serp_lookup runs, the richer this gets — that's the proprietary asset.

    Args:
        market: Two-letter country/language code.
        limit: Max competitors to return.
    """
    comps = store.competitors_from_index(market, limit)
    if not comps:
        return {"status": "empty",
                "reason": "Index is empty — run serp_lookup on the niche's head queries "
                "first to build the owned competitor index."}
    return {"status": "success", "competitors": comps,
            "note": "Ranked by how many indexed queries each domain appears for."}


@mcp.tool()
def keyword_volume(keywords: str, market: str = "us") -> dict:
    """Real search volume via Google Ads Keyword Planner (FREE with an Ads account).

    Volume is Google's proprietary data — Keyword Planner is the only free source.
    Requires Google Ads API OAuth (developer token + refresh token). Returns
    not_configured until wired; never fabricates volumes.

    Args:
        keywords: Comma-separated keywords.
        market: Two-letter country code.
    """
    if not os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"):
        return {"status": "not_configured",
                "reason": "Exact volume needs Google Ads Keyword Planner (free Ads "
                "account). Set GOOGLE_ADS_* credentials to enable. Until then, use "
                "keyword_ideas (demand signal) + keyword_difficulty (our score)."}
    return {"status": "not_implemented",
            "reason": "Wire the Google Ads GenerateKeywordIdeas call here once the Ads "
            "developer token + OAuth refresh token are provisioned."}


@mcp.tool()
def seed_index(seeds: str, market: str = "us") -> dict:
    """Bootstrap the owned competitor index by fetching SERPs for seed queries.

    Runs serp_lookup over each seed + its top autocomplete expansions, recording
    who ranks into our SQLite index. After this, organic_competitors returns real
    competitors. Requires SEARXNG_URL. This is how the owned dataset is born.

    Args:
        seeds: Comma-separated head queries for the niche.
        market: Two-letter country/language code.
    """
    if not os.environ.get("SEARXNG_URL"):
        return {"status": "not_configured",
                "reason": "seed_index needs SEARXNG_URL (self-hosted SearXNG) to fetch "
                "SERPs. Set it, then re-run to build your owned competitor index."}
    queries: list[str] = []
    for seed in [s.strip() for s in seeds.split(",") if s.strip()]:
        queries.append(seed)
        queries.extend(_suggest(seed, market)[:5])  # a few real expansions per seed
    seen, fetched, errors = set(), 0, 0
    for q in queries:
        if q in seen:
            continue
        seen.add(q)
        res = serp_lookup(q, market)
        if res.get("status") == "success":
            fetched += 1
        else:
            errors += 1
    comps = store.competitors_from_index(market, 10)
    return {"status": "success", "queries_fetched": fetched, "queries_failed": errors,
            "top_competitors": comps, "index": store.stats()}


@mcp.tool()
def index_stats() -> dict:
    """Report how big our owned SEO index has grown (keywords/SERP rows/domains)."""
    return {"status": "success", **store.stats()}


if __name__ == "__main__":
    mcp.run()  # stdio transport
