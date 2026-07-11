# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Gated CMS publishing.

An abstract `Publisher` with a safe stub adapter (default) plus Webflow/Shopify
adapters you activate by setting CMS_PLATFORM + credentials. The `publish_change`
tool is doubly guarded by the runtime callback: blocked outside the implement
phase AND blocked until state['publish_approved'] is True.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from google.adk.tools.tool_context import ToolContext


class Publisher(ABC):
    """Adapter interface. Implement one per CMS."""

    platform: str = "abstract"

    @abstractmethod
    def apply(self, target: str, field: str, value: str) -> dict:
        """Apply a single field change to a CMS resource."""
        raise NotImplementedError


class StubPublisher(Publisher):
    """Default: records the intended change without touching any live site.
    Lets the whole pipeline run end-to-end safely before real creds exist."""

    platform = "stub"

    def apply(self, target: str, field: str, value: str) -> dict:
        return {"status": "recorded_dry_run", "platform": self.platform,
                "target": target, "field": field, "value_preview": value[:200],
                "note": "No live site configured; change logged only."}


class WebflowPublisher(Publisher):
    """Webflow CMS adapter (fill in with the Webflow Data API v2)."""

    platform = "webflow"

    def apply(self, target: str, field: str, value: str) -> dict:
        token = os.environ.get("WEBFLOW_API_TOKEN")
        if not token:
            return {"status": "not_configured", "reason": "Set WEBFLOW_API_TOKEN."}
        # TODO: PATCH https://api.webflow.com/v2/collections/{id}/items/{item}
        return {"status": "not_implemented",
                "reason": "Wire the Webflow Data API call here once the collection/"
                "item mapping is confirmed."}


class ShopifyPublisher(Publisher):
    """Shopify Admin API adapter (products/pages/articles + SEO metafields)."""

    platform = "shopify"

    def apply(self, target: str, field: str, value: str) -> dict:
        token = os.environ.get("SHOPIFY_ADMIN_TOKEN")
        store = os.environ.get("SHOPIFY_STORE_DOMAIN")
        if not token or not store:
            return {"status": "not_configured",
                    "reason": "Set SHOPIFY_ADMIN_TOKEN and SHOPIFY_STORE_DOMAIN."}
        # TODO: PUT https://{store}/admin/api/2024-10/{resource}.json (+ metafields)
        return {"status": "not_implemented",
                "reason": "Wire the Shopify Admin API call here once resource type "
                "(product/page/article) is confirmed."}


def _get_publisher() -> Publisher:
    platform = (os.environ.get("CMS_PLATFORM") or "stub").lower()
    return {"webflow": WebflowPublisher, "shopify": ShopifyPublisher}.get(
        platform, StubPublisher
    )()


def publish_change(target: str, field: str, value: str, tool_context: ToolContext) -> dict:
    """Apply ONE approved SEO change to the live CMS (gated).

    Blocked unless phase == implement AND state['publish_approved'] is True. Every
    call is appended to the change_log for documentation.

    Args:
        target: The CMS resource id or URL to edit.
        field: The field to change (e.g. 'seo_title', 'meta_description', 'body').
        value: The new value.
    """
    pub = _get_publisher()
    result = pub.apply(target, field, value)

    log = list(tool_context.state.get("change_log") or [])
    log.append({"target": target, "field": field, "value_preview": value[:200],
                "platform": pub.platform, "result_status": result.get("status")})
    tool_context.state["change_log"] = log
    return result
