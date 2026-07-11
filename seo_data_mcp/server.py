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

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("seo-data")

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
    return {"status": "success", "seed": seed, "market": market,
            "count": len(ordered), "keywords": ordered,
            "note": "Real autocomplete queries; no volume/difficulty (needs paid index)."}


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


if __name__ == "__main__":
    mcp.run()  # stdio transport
