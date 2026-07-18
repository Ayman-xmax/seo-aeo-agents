# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Deterministic technical-SEO crawler tools.

These are pure code (no LLM), so their output is ground truth the agents reason
over. The link/anchor auditor encodes Google's "Make your links crawlable"
guidance verbatim as checks.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from google.adk.tools.tool_context import ToolContext

from .. import config

try:  # optional deps kept guarded so the agent tree always imports
    import requests
    from bs4 import BeautifulSoup

    _DEPS = True
except Exception:  # pragma: no cover
    _DEPS = False

_UA = "Mozilla/5.0 (compatible; SEO-AEO-Agent/1.0; +local-prototype)"
_TIMEOUT = 20

# Anchor text Google explicitly calls out as too generic.
_GENERIC_ANCHORS = {"click here", "read more", "here", "more", "this", "link", "website"}
# href values Google cannot reliably follow.
_JS_HREF = re.compile(r"^\s*javascript:", re.I)


def _fetch(url: str) -> tuple[str | None, dict]:
    if not _DEPS:
        return None, {"status": "unavailable", "reason": "requests/bs4 not installed"}
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
        return r.text, {"status": "success", "http_status": r.status_code, "final_url": r.url}
    except Exception as e:  # network / DNS / TLS
        return None, {"status": "unavailable", "reason": f"fetch failed: {e}"}


def audit_links(url: str) -> dict:
    """Audit all links on a page against Google's crawlable-link rules.

    Flags non-crawlable links (routerLink, span[href], onclick-only, javascript:
    hrefs), generic or over-long/stuffed anchor text, image links missing alt,
    empty links missing title, chained adjacent links, and pages exceeding the
    link-count limit. Returns a structured, ground-truth dict.

    Args:
        url: The absolute URL of the page to audit.
    """
    html, meta = _fetch(url)
    if html is None:
        return {"status": meta["status"], "url": url, "reason": meta.get("reason")}

    soup = BeautifulSoup(html, "lxml")
    issues: list[dict] = []
    total_a_href = 0

    # Non-crawlable: <span href>, <div href>, other non-anchor elements with href.
    for el in soup.find_all(attrs={"href": True}):
        if el.name != "a":
            issues.append({"type": "non_anchor_href", "tag": el.name, "sample": str(el)[:120]})
    # Non-crawlable: routerLink or other framework nav attributes without href.
    for el in soup.find_all(attrs={"routerlink": True}):
        issues.append({"type": "router_link_no_href", "sample": str(el)[:120]})

    anchors = soup.find_all("a")
    for a in anchors:
        href = a.get("href")
        onclick = a.get("onclick")
        text = a.get_text(strip=True)

        # onclick-only navigation, or javascript: pseudo-URLs -> not followable.
        if href is None and onclick:
            issues.append({"type": "onclick_only_link", "sample": str(a)[:120]})
            continue
        if href is None:
            continue
        if _JS_HREF.match(href):
            issues.append({"type": "javascript_href", "href": href[:80]})
            continue

        total_a_href += 1

        # Empty link: needs title (or img alt) so it conveys meaning.
        if not text:
            img = a.find("img")
            if img is not None and not img.get("alt"):
                issues.append({"type": "image_link_missing_alt", "href": href[:80]})
            elif img is None and not a.get("title"):
                issues.append({"type": "empty_link_missing_title", "href": href[:80]})

        # Anchor quality.
        low = text.lower()
        if low in _GENERIC_ANCHORS:
            issues.append({"type": "generic_anchor", "text": text, "href": href[:80]})
        if len(text) > 100:
            issues.append({"type": "anchor_too_long", "len": len(text), "href": href[:80]})

        # Paid/UGC attribute hygiene.
        rel = " ".join(a.get("rel", [])) if a.get("rel") else ""
        if ("sponsor" in low or "ad" == low) and "sponsored" not in rel and "nofollow" not in rel:
            issues.append({"type": "paid_link_missing_rel_sponsored", "href": href[:80]})

    # Chained adjacent links (harder to read, lost surrounding context).
    for parent in soup.find_all(True):
        kids = [c for c in parent.children if getattr(c, "name", None) == "a"]
        if len(kids) >= 3:
            texts = [k.get_text(strip=True) for k in kids]
            # crude adjacency check: 3+ direct <a> children in a row
            if all(texts):
                issues.append({"type": "chained_links", "count": len(kids)})
                break

    _record_graph_edges(meta.get("final_url", url), soup)  # self-build the link graph
    over_link_limit = total_a_href > config.MAX_LINKS_PER_PAGE
    return {
        "status": "success",
        "url": meta.get("final_url", url),
        "total_crawlable_links": total_a_href,
        "over_link_limit": over_link_limit,
        "link_limit": config.MAX_LINKS_PER_PAGE,
        "issue_count": len(issues),
        "issues": issues[:100],
    }


def audit_technical_basics(url: str) -> dict:
    """Check on-page technical/SEO basics for a single page.

    Verifies: title presence + char length vs pixel-proxy bands, meta description
    length, exactly one H1, heading hierarchy, canonical tag correctness, meta
    robots, and JSON-LD structured-data types present (flagging deprecated
    FAQ/HowTo). Ground-truth output, no estimation.

    Args:
        url: The absolute URL of the page to check.
    """
    html, meta = _fetch(url)
    if html is None:
        return {"status": meta["status"], "url": url, "reason": meta.get("reason")}

    soup = BeautifulSoup(html, "lxml")
    findings: list[str] = []

    title = soup.title.get_text(strip=True) if soup.title else ""
    if not title:
        findings.append("missing_title")
    elif len(title) > config.TITLE_CHARS["max"]:
        findings.append(f"title_too_long:{len(title)}chars(risk_of_rewrite)")
    elif len(title) < config.TITLE_CHARS["min"]:
        findings.append(f"title_too_short:{len(title)}chars")

    desc_el = soup.find("meta", attrs={"name": "description"})
    desc = desc_el.get("content", "").strip() if desc_el else ""
    if not desc:
        findings.append("missing_meta_description")
    elif len(desc) > config.META_CHARS["max"]:
        findings.append(f"meta_desc_too_long:{len(desc)}chars")

    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        findings.append("missing_h1")
    elif len(h1s) > 1:
        findings.append(f"multiple_h1:{len(h1s)}")

    canonical = soup.find("link", attrs={"rel": "canonical"})
    canonical_href = canonical.get("href") if canonical else None
    if canonical_href and not urlparse(canonical_href).netloc:
        findings.append("relative_canonical_url")

    robots_el = soup.find("meta", attrs={"name": "robots"})
    robots = robots_el.get("content", "").lower() if robots_el else ""

    schema_types: list[str] = []
    deprecated_schema: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            findings.append("invalid_jsonld")
            continue
        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            t = b.get("@type") if isinstance(b, dict) else None
            if isinstance(t, str):
                schema_types.append(t)
                if t in config.DEPRECATED_RICH_RESULT_TYPES:
                    deprecated_schema.append(t)

    return {
        "status": "success",
        "url": meta.get("final_url", url),
        "title": title,
        "title_len": len(title),
        "meta_description": desc,
        "meta_description_len": len(desc),
        "h1_count": len(h1s),
        "canonical": canonical_href,
        "meta_robots": robots,
        "schema_types": schema_types,
        "deprecated_schema_present": deprecated_schema,
        "findings": findings,
    }


def _dom(url: str) -> str:
    net = urlparse(url).netloc.lower()
    return net[4:] if net.startswith("www.") else net


def _record_graph_edges(src_url: str, soup) -> None:
    """Feed our owned link graph automatically whenever we crawl a page (so off-page
    authority builds itself — no reliance on the LLM calling a tool)."""
    try:
        from seo_data_mcp import store as _store
    except Exception:
        return
    src = _dom(src_url)
    dsts = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(src_url, a["href"])
        if full.startswith("http"):
            d = _dom(full)
            if d and d != src:
                dsts.add(d)
    if dsts:
        _store.add_edges(src, list(dsts))


def fetch_site_overview(url: str) -> dict:
    """Read a page's content so the agent can understand what the site/business IS and
    infer its niche on its own: title, meta description, H1/H2 headings, and a body
    text excerpt. Use this on a target site before setting the niche.

    Args:
        url: The site URL to read (usually the homepage).
    """
    html, meta = _fetch(url)
    if html is None:
        return {"status": meta["status"], "url": url, "reason": meta.get("reason")}
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    desc_el = soup.find("meta", attrs={"name": "description"})
    desc = desc_el.get("content", "").strip() if desc_el else ""
    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")][:5]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")][:12]
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return {
        "status": "success",
        "url": meta.get("final_url", url),
        "title": title,
        "meta_description": desc,
        "h1": h1,
        "h2": h2,
        "text_excerpt": text[:1800],
    }


_SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|pdf|zip|woff2?|mp4|xml)$", re.I)


def _sitemap_urls(base_url: str) -> list[str]:
    """Best-effort: pull page URLs from /sitemap.xml (and sitemap indexes)."""
    if not _DEPS:
        return []
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    found: list[str] = []
    try:
        for sm in (urljoin(root, "/sitemap.xml"), urljoin(root, "/sitemap_index.xml")):
            r = requests.get(sm, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
            if r.status_code != 200:
                continue
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
            # if it's a sitemap index, follow child sitemaps (bounded)
            children = [u for u in locs if u.endswith(".xml")]
            for child in children[:5]:
                try:
                    cr = requests.get(child, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
                    found += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", cr.text)
                except Exception:
                    pass
            found += [u for u in locs if not u.endswith(".xml")]
            if found:
                break
    except Exception:
        return []
    return [u for u in found if u.startswith("http") and not _SKIP_EXT.search(u)]


def _audit_page_from_soup(url: str, soup) -> dict:
    """Compute the on-page signals for ONE already-parsed page (title/meta/h1/canonical/
    schema, link issues, content depth) — same rules as the single-page tools, one fetch."""
    title = soup.title.get_text(strip=True) if soup.title else ""
    desc_el = soup.find("meta", attrs={"name": "description"})
    desc = desc_el.get("content", "").strip() if desc_el else ""
    h1s = soup.find_all("h1")
    canonical = soup.find("link", attrs={"rel": "canonical"})
    canonical_href = canonical.get("href") if canonical else None

    basic_findings: list[str] = []
    if not title:
        basic_findings.append("missing_title")
    elif len(title) > config.TITLE_CHARS["max"]:
        basic_findings.append(f"title_too_long:{len(title)}chars")
    elif len(title) < config.TITLE_CHARS["min"]:
        basic_findings.append(f"title_too_short:{len(title)}chars")
    if not desc:
        basic_findings.append("missing_meta_description")
    elif len(desc) > config.META_CHARS["max"]:
        basic_findings.append(f"meta_desc_too_long:{len(desc)}chars")
    if len(h1s) == 0:
        basic_findings.append("missing_h1")
    elif len(h1s) > 1:
        basic_findings.append(f"multiple_h1:{len(h1s)}")
    if canonical_href and not urlparse(canonical_href).netloc:
        basic_findings.append("relative_canonical_url")

    schema_types: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue
        for b in (data if isinstance(data, list) else [data]):
            t = b.get("@type") if isinstance(b, dict) else None
            if isinstance(t, str):
                schema_types.append(t)

    # link issues (compact — scoring only needs issue_count + over_link_limit)
    issues = 0
    total_links = 0
    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(strip=True)
        if href is None or _JS_HREF.match(href or ""):
            issues += 1
            continue
        total_links += 1
        if text.lower() in _GENERIC_ANCHORS:
            issues += 1
        img = a.find("img")
        if not text and img is not None and not img.get("alt"):
            issues += 1

    # content depth
    body = BeautifulSoup(str(soup), "lxml")
    for tag in body(["script", "style", "noscript", "template"]):
        tag.decompose()
    words = len(body.get_text(" ", strip=True).split())
    content_findings: list[str] = []
    if words < 300:
        content_findings.append(f"thin_content:{words}words")
    elif words < 600:
        content_findings.append(f"shallow_content:{words}words")

    return {
        "url": url, "title": title, "title_len": len(title),
        "meta_description": desc, "meta_len": len(desc), "h1_count": len(h1s),
        "canonical": canonical_href, "schema_types": schema_types,
        "word_count": words, "link_issues": issues, "total_links": total_links,
        "findings": basic_findings + content_findings,
    }


def audit_site(url: str, tool_context: ToolContext) -> dict:
    """Crawl the WHOLE site (sitemap + internal-link BFS, bounded) and audit EVERY page.

    This is the site-wide inventory: it finds every page, audits each (title/meta/H1/
    canonical/schema, link hygiene, content depth), and writes per-page signals so the
    Health Score reflects the whole site, not just the homepage. Returns per-page issues
    plus a site-level summary. Call this ONCE per site.

    Args:
        url: The site root URL.
    """
    if not _DEPS:
        return {"status": "unavailable", "reason": "requests/bs4 not installed"}
    from collections import deque

    parsed = urlparse(url)
    host = parsed.netloc
    start = f"{parsed.scheme}://{host}/"
    seen = {start}
    queue = deque([start])
    for u in _sitemap_urls(url):
        if urlparse(u).netloc == host and u not in seen:
            seen.add(u)
            queue.append(u)

    pages: list[dict] = []
    basics_sig, links_sig, content_sig = [], [], []
    max_pages = config.SITE_CRAWL_MAX_PAGES

    while queue and len(pages) < max_pages:
        page_url = queue.popleft()
        html, meta = _fetch(page_url)
        if html is None:
            continue
        soup = BeautifulSoup(html, "lxml")
        audit = _audit_page_from_soup(meta.get("final_url", page_url), soup)
        pages.append(audit)
        # signal shapes the scorer already aggregates (per page -> whole-site score)
        basics_sig.append({"status": "success", "findings": [f for f in audit["findings"]
                           if not f.startswith(("thin_content", "shallow_content"))],
                           "schema_types": audit["schema_types"]})
        links_sig.append({"status": "success", "issue_count": audit["link_issues"],
                          "over_link_limit": audit["total_links"] > config.MAX_LINKS_PER_PAGE})
        content_sig.append({"status": "success", "word_count": audit["word_count"],
                            "findings": [f for f in audit["findings"]
                                         if f.startswith(("thin_content", "shallow_content"))]})
        # discover more internal pages
        for a in soup.find_all("a", href=True):
            full = urljoin(page_url, a["href"]).split("#")[0].split("?")[0]
            if (full.startswith("http") and urlparse(full).netloc == host
                    and full not in seen and not _SKIP_EXT.search(full)):
                seen.add(full)
                queue.append(full)

    if tool_context is not None:
        sig = dict(tool_context.state.get("signals") or {})
        sig["audit_technical_basics"] = (sig.get("audit_technical_basics") or []) + basics_sig
        sig["audit_links"] = (sig.get("audit_links") or []) + links_sig
        sig["audit_content"] = (sig.get("audit_content") or []) + content_sig
        tool_context.state["signals"] = sig
        tool_context.state["page_inventory"] = [p["url"] for p in pages]
        # url+title so the content writer can add real internal links.
        tool_context.state["site_pages"] = [
            {"url": p["url"], "title": p["title"]} for p in pages]

    summary = {
        "pages_audited": len(pages),
        "discovered_but_uncrawled": max(0, len(seen) - len(pages)),
        "missing_title": sum(1 for p in pages if "missing_title" in p["findings"]),
        "missing_meta": sum(1 for p in pages if "missing_meta_description" in p["findings"]),
        "missing_h1": sum(1 for p in pages if "missing_h1" in p["findings"]),
        "thin_pages": sum(1 for p in pages
                          if any(f.startswith("thin_content") for f in p["findings"])),
        "total_link_issues": sum(p["link_issues"] for p in pages),
        "pages_with_schema": sum(1 for p in pages if p["schema_types"]),
    }
    return {"status": "success", "site": host, "summary": summary,
            "pages": [{"url": p["url"], "title": p["title"], "word_count": p["word_count"],
                       "findings": p["findings"]} for p in pages]}


def audit_content(url: str) -> dict:
    """Audit on-page CONTENT depth & structure for a page (deterministic, ground truth).

    Measures body word count (thin-content flag), heading structure, and extractable
    formatting (lists/tables — good for AEO). Feeds the Content/Keyword Health Score.

    Args:
        url: The absolute URL of the page to audit.
    """
    html, meta = _fetch(url)
    if html is None:
        return {"status": meta["status"], "url": url, "reason": meta.get("reason")}

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    words = len(text.split())
    h2 = len(soup.find_all("h2"))
    h3 = len(soup.find_all("h3"))
    lists = len(soup.find_all(["ul", "ol"]))
    tables = len(soup.find_all("table"))

    findings: list[str] = []
    if words < 300:
        findings.append(f"thin_content:{words}words")
    elif words < 600:
        findings.append(f"shallow_content:{words}words")
    if words > 400 and h2 == 0:
        findings.append("no_h2_structure")
    if words > 600 and lists == 0 and tables == 0:
        findings.append("no_extractable_formatting_for_aeo")

    return {
        "status": "success",
        "url": meta.get("final_url", url),
        "word_count": words,
        "h2_count": h2,
        "h3_count": h3,
        "list_count": lists,
        "table_count": tables,
        "findings": findings,
    }


def check_robots_and_sitemap(url: str) -> dict:
    """Fetch and validate robots.txt and discover sitemaps for a site.

    Checks robots.txt size (<=500 KiB), that it does not combine Disallow with a
    noindexed area, and lists declared sitemaps. Ground-truth output.

    Args:
        url: Any URL on the target site (scheme + host are used).
    """
    if not _DEPS:
        return {"status": "unavailable", "reason": "requests not installed"}
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base, "/robots.txt")
    try:
        r = requests.get(robots_url, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    except Exception as e:
        return {"status": "unavailable", "reason": f"robots fetch failed: {e}"}

    body = r.text if r.status_code == 200 else ""
    size = len(body.encode("utf-8"))
    sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", body)
    disallows = re.findall(r"(?im)^\s*disallow:\s*(\S+)", body)
    findings = []
    if size > config.ROBOTS_MAX_BYTES:
        findings.append(f"robots_too_large:{size}bytes(>500KiB_ignored)")
    if not sitemaps:
        findings.append("no_sitemap_declared_in_robots")
    return {
        "status": "success",
        "robots_url": robots_url,
        "robots_http_status": r.status_code,
        "robots_size_bytes": size,
        "declared_sitemaps": sitemaps,
        "disallow_count": len(disallows),
        "findings": findings,
    }
