# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Site-building tools so Phase 2 can CREATE and IMPLEMENT structural changes, not just
edit head tags: generate a sitemap, write robots.txt, and create new pages.

All write to SITE_REPO_PATH when set (git = rollback); otherwise they return the
generated content for manual placement. Gated by the runtime callback (implement phase
+ approval), same as publish_change.
"""

from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

from google.adk.tools.tool_context import ToolContext

try:
    import requests
    from bs4 import BeautifulSoup

    _DEPS = True
except Exception:  # pragma: no cover
    _DEPS = False

_UA = "Mozilla/5.0 (compatible; SEO-AEO-Agent/1.0)"


def _repo() -> str | None:
    return os.environ.get("SITE_REPO_PATH")


def generate_sitemap(base_url: str, tool_context: ToolContext) -> dict:
    """Crawl the site's internal links and generate a valid sitemap.xml.

    Writes it to SITE_REPO_PATH/sitemap.xml when set; otherwise returns the XML.

    Args:
        base_url: The site root, e.g. 'https://holisticpathtechnologies.com/'.
    """
    if not _DEPS:
        return {"status": "unavailable", "reason": "requests/bs4 not installed"}
    host = urlparse(base_url).netloc
    urls = {base_url.rstrip("/") + "/"}
    try:
        r = requests.get(base_url, headers={"User-Agent": _UA}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            full = urljoin(base_url, a["href"]).split("#")[0]
            if full.startswith("http") and urlparse(full).netloc == host:
                urls.add(full)
    except Exception as e:
        return {"status": "unavailable", "reason": f"crawl failed: {e}"}

    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in sorted(urls))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")

    repo = _repo()
    log = list(tool_context.state.get("change_log") or [])
    if repo:
        path = os.path.join(repo, "sitemap.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        log.append({"target": "sitemap.xml", "field": "sitemap", "platform": "static",
                    "result_status": "applied_to_file"})
        tool_context.state["change_log"] = log
        return {"status": "applied_to_file", "file": path, "url_count": len(urls),
                "note": "Declare it in robots.txt (write_robots) and submit in GSC."}
    return {"status": "generated", "url_count": len(urls), "sitemap_xml": xml,
            "note": "Set SITE_REPO_PATH to write it, or paste this at /sitemap.xml."}


def write_robots(sitemap_url: str, tool_context: ToolContext) -> dict:
    """Create/refresh robots.txt that allows crawling and declares the sitemap.

    Args:
        sitemap_url: Full sitemap URL, e.g. 'https://example.com/sitemap.xml'.
    """
    content = f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"
    repo = _repo()
    if repo:
        path = os.path.join(repo, "robots.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log = list(tool_context.state.get("change_log") or [])
        log.append({"target": "robots.txt", "field": "robots", "platform": "static",
                    "result_status": "applied_to_file"})
        tool_context.state["change_log"] = log
        return {"status": "applied_to_file", "file": path}
    return {"status": "generated", "robots_txt": content,
            "note": "Set SITE_REPO_PATH to write it, or paste this at /robots.txt."}


def create_page(path: str, title: str, meta_description: str, heading: str,
                body_html: str, tool_context: ToolContext) -> dict:
    """Create a NEW SEO-ready HTML page (for content-brief pages).

    Writes to SITE_REPO_PATH/<path> when set; otherwise returns the HTML.

    Args:
        path: Relative file path, e.g. 'what-is-custom-software-development.html'.
        title: <title> text (~55 chars).
        meta_description: Meta description (~155 chars).
        heading: The page H1 text.
        body_html: The page body HTML (headings, paragraphs, lists).
    """
    html = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"  <title>{title}</title>\n"
        f"  <meta name=\"description\" content=\"{meta_description}\">\n"
        "</head>\n<body>\n"
        f"  <h1>{heading}</h1>\n{body_html}\n</body>\n</html>\n"
    )
    repo = _repo()
    log = list(tool_context.state.get("change_log") or [])
    if repo:
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(html)
        log.append({"target": path, "field": "new_page", "platform": "static",
                    "result_status": "applied_to_file"})
        tool_context.state["change_log"] = log
        return {"status": "applied_to_file", "file": full,
                "note": "New page created — add it to your nav + sitemap."}
    return {"status": "generated", "path": path, "html": html,
            "note": "Set SITE_REPO_PATH to write it, or save this HTML at the path."}
