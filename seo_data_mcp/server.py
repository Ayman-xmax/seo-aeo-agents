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

import gzip
import os
from collections import defaultdict
from statistics import mean
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

from . import authority, store


def _cc_reverse_domain(reversed_host: str) -> str:
    """Common Crawl stores hosts reversed ('org.python' -> 'python.org')."""
    return ".".join(reversed(reversed_host.split(".")))


def _ddg_serp(query: str, market: str) -> list[dict]:
    """ORGANIC SERP: fetch + parse DuckDuckGo's HTML endpoint ourselves. No API key,
    no third-party SEO service — just our own request and parser."""
    r = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query, "kl": f"{market}-en"},
        headers={"User-Agent": _UA}, timeout=20,
    )
    soup = BeautifulSoup(r.text, "lxml")
    rows: list[dict] = []
    for i, a in enumerate(soup.select("a.result__a")[:10]):
        href = a.get("href", "")
        url = href
        if "uddg=" in href:  # DDG wraps the real URL in a redirect param
            qs = parse_qs(urlparse(href).query)
            url = unquote(qs.get("uddg", [href])[0])
        if url.startswith("http"):
            rows.append({"rank": i + 1, "domain": _domain_of(url), "url": url})
    return rows

mcp = FastMCP("seo-data")


def _domain_of(url: str) -> str:
    net = urlparse(url).netloc.lower()
    return net[4:] if net.startswith("www.") else net


def _outbound_domains(url: str) -> tuple[str, set[str]]:
    """Fetch a page and return (its domain, set of external domains it links to)."""
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=8)
    src = _domain_of(r.url)
    soup = BeautifulSoup(r.text, "lxml")
    dsts: set[str] = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(r.url, a["href"])
        if full.startswith("http"):
            d = _domain_of(full)
            if d and d != src:
                dsts.add(d)
    return src, dsts

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
def crawl_links(url: str) -> dict:
    """Crawl one page and record its outbound domain links into our OWN link graph.

    This is how we build the graph that authority is computed from — no third-party
    data. Crawl the target site + competitors + niche pages (e.g. serp_lookup URLs),
    then call compute_authority.

    Args:
        url: The page URL to crawl for outbound links.
    """
    try:
        src, dsts = _outbound_domains(url)
        added = store.add_edges(src, list(dsts))
        return {"status": "success", "source_domain": src,
                "outbound_domains": len(dsts), "edges_added": added,
                "sample": sorted(dsts)[:20]}
    except Exception as e:
        return {"status": "unavailable", "reason": f"crawl failed: {e}"}


@mcp.tool()
def compute_authority() -> dict:
    """Run PageRank over our crawled link graph -> 0-100 authority for every domain.

    Same mechanism as Ahrefs DR / Semrush AS / Open PageRank, but computed locally on
    our own graph. Run after crawling; re-run as the graph grows.
    """
    return authority.compute_pagerank()


@mcp.tool()
def domain_authority(domain: str) -> dict:
    """OUR computed domain authority (0-100), from local PageRank — no paid API.

    Reads the score produced by compute_authority. If the domain isn't in our graph
    yet, crawl pages that link to it, then compute_authority.

    Args:
        domain: Bare domain, e.g. 'example.com'.
    """
    rec = store.get_authority(domain)
    if not rec:
        return {"status": "not_in_graph", "domain": domain,
                "reason": "Domain not scored yet. crawl_links on pages in its niche "
                "(and the domain itself), then compute_authority."}
    return {"status": "success", "domain": domain,
            "authority_0_100": rec["score"], "graph_rank": rec["rank"],
            "source": "local_pagerank",
            "referring_domains_known": len(store.referring_domains(domain, 1000))}


@mcp.tool()
def referring_domains(domain: str, limit: int = 100) -> dict:
    """Domains that link TO `domain` in our crawled graph = discovered backlinks.

    Args:
        domain: Bare domain to look up backlinks for.
        limit: Max referring domains to return.
    """
    refs = store.referring_domains(domain, limit)
    return {"status": "success", "domain": domain, "referring_domains_count": len(refs),
            "referring_domains": refs,
            "note": "Backlinks discovered by our own crawl; coverage grows as you crawl "
            "more of the niche."}


@mcp.tool()
def serp_lookup(query: str, market: str = "us") -> dict:
    """Top organic domains for a query — works out of the box, no external SEO service.

    Default: we fetch + parse the SERP ourselves (organic). If you self-host SearXNG
    and set SEARXNG_URL, it uses that instead. Results accumulate in our owned SERP
    index (powers competitor discovery + keyword difficulty).

    Args:
        query: The search query.
        market: Two-letter country/language code.
    """
    base = os.environ.get("SEARXNG_URL")
    try:
        if base:
            r = requests.get(f"{base.rstrip('/')}/search",
                             params={"q": query, "format": "json", "language": market},
                             headers={"User-Agent": _UA}, timeout=20)
            results = r.json().get("results", [])
            rows = [{"rank": i + 1, "domain": _domain_of(x["url"]), "url": x["url"]}
                    for i, x in enumerate(results[:10]) if x.get("url")]
            source = "searxng"
        else:
            rows = _ddg_serp(query, market)  # organic, no key, no third-party API
            source = "organic_ddg"
        store.record_serp(query, market, rows)  # accumulate = ownership
        return {"status": "success", "query": query, "source": source,
                "count": len(rows), "rows": rows}
    except Exception as e:
        return {"status": "unavailable", "reason": f"SERP fetch failed: {e}"}


@mcp.tool()
def keyword_difficulty(keyword: str, market: str = "us") -> dict:
    """OUR OWN keyword difficulty (0-100) — fully organic, no external SEO API.

    Fetches the SERP (organic), builds our link graph from the ranking pages, runs
    local PageRank, and averages the top domains' authority: stronger incumbents =>
    harder. Our formula, our data. Honest: an approximation, not Semrush's.

    Args:
        keyword: The keyword to score.
        market: Two-letter country/language code.
    """
    serp = serp_lookup(keyword, market)
    if serp.get("status") != "success" or not serp.get("rows"):
        return {"status": "unavailable",
                "reason": "Could not fetch a SERP for this keyword (try again)."}
    for row in serp["rows"][:5]:
        crawl_links(row["url"])  # build the graph from the top ranking pages (bounded)
    authority.compute_pagerank()
    scores = [rec["score"] for row in serp["rows"]
              if (rec := store.get_authority(row["domain"])) is not None]
    if not scores:
        return {"status": "unavailable", "reason": "Authority graph could not be built."}
    kd = round(mean(scores))
    return {"status": "success", "keyword": keyword, "difficulty_0_100": kd,
            "sampled_domains": len(scores),
            "basis": "mean local-PageRank authority of top ranking domains (organic, ours)"}


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

    Runs serp_lookup (organic — no external service) over each seed + its top
    autocomplete expansions, recording who ranks into our SQLite index and building
    the link graph. After this, organic_competitors returns real competitors. This is
    how the owned dataset is born.

    Args:
        seeds: Comma-separated head queries for the niche.
        market: Two-letter country/language code.
    """
    queries: list[str] = []
    for seed in [s.strip() for s in seeds.split(",") if s.strip()]:
        queries.append(seed)
        queries.extend(_suggest(seed, market)[:5])  # a few real expansions per seed
    seen, fetched, errors, crawled = set(), 0, 0, 0
    for q in queries:
        if q in seen:
            continue
        seen.add(q)
        res = serp_lookup(q, market)
        if res.get("status") != "success":
            errors += 1
            continue
        fetched += 1
        # Self-build the link graph: crawl the top ranking pages (bounded for latency).
        for row in res.get("rows", [])[:2]:
            if crawled < 8 and crawl_links(row["url"]).get("status") == "success":
                crawled += 1
    pr = compute_authority() if crawled else {"status": "empty"}
    comps = store.competitors_from_index(market, 10)
    return {"status": "success", "queries_fetched": fetched, "queries_failed": errors,
            "pages_crawled": crawled, "authority": pr, "top_competitors": comps,
            "index": store.stats()}


@mcp.tool()
def bootstrap_authority(urls: str, market: str = "us") -> dict:
    """One-call authority: crawl a set of URLs (target + competitors), build the link
    graph, run PageRank, and return the scores. No SearXNG needed — just URLs.

    Args:
        urls: Comma-separated URLs (the target site + a few competitor/niche pages).
        market: Two-letter country/language code (unused; for interface parity).
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        return {"status": "error", "reason": "Provide at least one URL."}
    crawled = 0
    for u in url_list:
        if crawl_links(u).get("status") == "success":
            crawled += 1
    pr = compute_authority()
    return {"status": "success", "urls_crawled": crawled, "pagerank": pr,
            "index": store.stats()}


@mcp.tool()
def seed_common_crawl(release: str, max_domains: int = 50000,
                      max_edges: int = 500000) -> dict:
    """WEB-SCALE authority for free: stream Common Crawl's open domain graph into our
    edge table (the same dataset Open PageRank uses), bounded by caps. Then run
    compute_authority. Downloads from Common Crawl; heavy — start with small caps.

    Args:
        release: CC web-graph release id, e.g. 'cc-main-2024-feb-mar-apr'
                 (verify current name at https://commoncrawl.org/web-graphs).
        max_domains: Cap on vertices to load (top by centrality come first).
        max_edges: Cap on edges to ingest.
    """
    base = f"https://data.commoncrawl.org/projects/hyperlinkgraph/{release}/domain"
    vurl = f"{base}/{release}-domain-vertices.txt.gz"
    eurl = f"{base}/{release}-domain-edges.txt.gz"
    try:
        id2dom: dict[int, str] = {}
        with requests.get(vurl, stream=True, timeout=120) as r:
            r.raise_for_status()
            r.raw.decode_content = False
            for raw in gzip.GzipFile(fileobj=r.raw):
                parts = raw.decode("utf-8", "ignore").rstrip().split("\t")
                if len(parts) >= 2:
                    id2dom[int(parts[0])] = _cc_reverse_domain(parts[1])
                if len(id2dom) >= max_domains:
                    break
        buf: dict[str, list[str]] = defaultdict(list)
        added = 0
        with requests.get(eurl, stream=True, timeout=300) as r:
            r.raise_for_status()
            r.raw.decode_content = False
            for raw in gzip.GzipFile(fileobj=r.raw):
                parts = raw.decode("utf-8", "ignore").rstrip().split("\t")
                if len(parts) == 2:
                    si, di = int(parts[0]), int(parts[1])
                    if si in id2dom and di in id2dom:
                        buf[id2dom[si]].append(id2dom[di])
                        added += 1
                        if added >= max_edges:
                            break
        for src, dsts in buf.items():
            store.add_edges(src, dsts)
        return {"status": "success", "vertices_loaded": len(id2dom),
                "edges_added": added,
                "note": "Now call compute_authority to score the web-scale graph."}
    except Exception as e:
        return {"status": "unavailable",
                "reason": f"Common Crawl seed failed: {e}. Check the release id at "
                "https://commoncrawl.org/web-graphs."}


@mcp.tool()
def index_stats() -> dict:
    """Report how big our owned SEO index has grown (keywords/SERP/graph)."""
    return {"status": "success", **store.stats()}


if __name__ == "__main__":
    mcp.run()  # stdio transport
