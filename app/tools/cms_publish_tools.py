# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Gated publishing (Phase 2).

Default target is a static/custom site: changes are emitted as a reviewable
change-set (organic, no external API), and — if SITE_REPO_PATH points at the
site's local repo — head-level SEO fields (title/meta/canonical/schema) are
applied directly to the files, leaving a git-diffable edit. Body/heading edits
always go to the change-set (auto-rewriting page bodies blind is unsafe).

Webflow/Shopify adapters remain available for CMS-hosted sites.

`publish_change` is doubly guarded by the runtime callback: blocked outside the
implement phase AND until state['publish_approved'] is True.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

from google.adk.tools.tool_context import ToolContext

# Head-level fields we can safely apply to a static HTML file.
_HEAD_FIELDS = {"seo_title", "title", "meta_description", "canonical",
                "schema_jsonld", "meta_robots"}
_CHANGESET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "seo_changes")


class Publisher(ABC):
    platform: str = "abstract"

    @abstractmethod
    def apply(self, target: str, field: str, value: str) -> dict:
        raise NotImplementedError


def _record_changeset(target: str, field: str, value: str, mode: str) -> str:
    """Append a change to a human-reviewable change-set file. Returns its path."""
    os.makedirs(_CHANGESET_DIR, exist_ok=True)
    path = os.path.join(_CHANGESET_DIR, "changeset.md")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {target}\n- **field:** {field}\n- **apply:** {mode}\n"
                f"- **new value:**\n\n```\n{value}\n```\n\n")
    return path


class StaticSitePublisher(Publisher):
    """Static/custom site: change-set by default; direct file edits for head fields
    when SITE_REPO_PATH is set. Git is the rollback mechanism."""

    platform = "static"

    def _resolve(self, target: str) -> str | None:
        repo = os.environ.get("SITE_REPO_PATH")
        if not repo:
            return None
        cand = target if os.path.isabs(target) else os.path.join(repo, target)
        return cand if os.path.isfile(cand) else None

    def _edit_head(self, path: str, field: str, value: str) -> bool:
        with open(path, encoding="utf-8") as f:
            html = f.read()
        if field in ("seo_title", "title"):
            new, n = re.subn(r"<title>.*?</title>", f"<title>{value}</title>",
                             html, count=1, flags=re.S | re.I)
        elif field == "meta_description":
            tag = f'<meta name="description" content="{value}">'
            new, n = re.subn(r'<meta\s+name=["\']description["\'][^>]*>', tag,
                             html, count=1, flags=re.I)
            if n == 0:  # insert before </head>
                new, n = re.subn(r"</head>", f"  {tag}\n</head>", html, count=1, flags=re.I)
        elif field == "canonical":
            tag = f'<link rel="canonical" href="{value}">'
            new, n = re.subn(r'<link\s+rel=["\']canonical["\'][^>]*>', tag,
                             html, count=1, flags=re.I)
            if n == 0:
                new, n = re.subn(r"</head>", f"  {tag}\n</head>", html, count=1, flags=re.I)
        elif field == "schema_jsonld":
            block = f'<script type="application/ld+json">\n{value}\n</script>'
            new, n = re.subn(r"</head>", f"  {block}\n</head>", html, count=1, flags=re.I)
        else:
            return False
        if n == 0:
            return False
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True

    def apply(self, target: str, field: str, value: str) -> dict:
        path = self._resolve(target)
        # Head fields with a resolved local file -> edit in place (git tracks it).
        if path and field in _HEAD_FIELDS and field != "meta_robots":
            try:
                if self._edit_head(path, field, value):
                    return {"status": "applied_to_file", "file": path, "field": field,
                            "note": "Edited in place — review with `git diff`."}
            except Exception as e:
                return {"status": "error", "reason": f"file edit failed: {e}",
                        "file": path}
        # Everything else (or no repo) -> reviewable change-set.
        cs = _record_changeset(target, field, value,
                               "manual (body/heading)" if field not in _HEAD_FIELDS
                               else "no SITE_REPO_PATH — apply manually")
        return {"status": "recorded_changeset", "changeset": cs, "target": target,
                "field": field, "note": "Added to the change-set for review/apply."}


class WebflowPublisher(Publisher):
    platform = "webflow"

    def apply(self, target: str, field: str, value: str) -> dict:
        if not os.environ.get("WEBFLOW_API_TOKEN"):
            return {"status": "not_configured", "reason": "Set WEBFLOW_API_TOKEN."}
        return {"status": "not_implemented",
                "reason": "Wire the Webflow Data API v2 call here."}


class ShopifyPublisher(Publisher):
    platform = "shopify"

    def apply(self, target: str, field: str, value: str) -> dict:
        if not (os.environ.get("SHOPIFY_ADMIN_TOKEN")
                and os.environ.get("SHOPIFY_STORE_DOMAIN")):
            return {"status": "not_configured",
                    "reason": "Set SHOPIFY_ADMIN_TOKEN and SHOPIFY_STORE_DOMAIN."}
        return {"status": "not_implemented",
                "reason": "Wire the Shopify Admin API call here."}


def _get_publisher() -> Publisher:
    platform = (os.environ.get("CMS_PLATFORM") or "static").lower()
    return {"webflow": WebflowPublisher, "shopify": ShopifyPublisher,
            "static": StaticSitePublisher}.get(platform, StaticSitePublisher)()


def publish_change(target: str, field: str, value: str, tool_context: ToolContext) -> dict:
    """Apply ONE approved SEO change (gated).

    For a static site: edits the file if SITE_REPO_PATH is set and it's a head field,
    else adds it to the reviewable change-set. Blocked unless phase == implement AND
    state['publish_approved'] is True. Every call is appended to change_log.

    Args:
        target: File path (relative to SITE_REPO_PATH) or URL to edit.
        field: 'seo_title' | 'meta_description' | 'canonical' | 'schema_jsonld' |
               'h1' | 'body' | ... .
        value: The new value / snippet.
    """
    pub = _get_publisher()
    result = pub.apply(target, field, value)
    log = list(tool_context.state.get("change_log") or [])
    log.append({"target": target, "field": field, "value_preview": value[:200],
                "platform": pub.platform, "result_status": result.get("status")})
    tool_context.state["change_log"] = log
    return result
