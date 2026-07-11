# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Semrush MCP toolset wiring.

Connects an ADK agent to a Semrush MCP server (keyword/organic/backlink/site-audit
research) via streamable HTTP. Returns None when not configured so the agent tree
still builds and collectors report data as `unavailable`.

Configure in app/.env:
    SEMRUSH_MCP_URL=https://<your-semrush-mcp-endpoint>/mcp
    SEMRUSH_MCP_API_KEY=<key>            # sent as X-API-Key header
"""

from __future__ import annotations

import os


def build_semrush_toolset(tool_filter: list[str] | None = None):
    """Return a configured McpToolset for Semrush, or None if unconfigured.

    Args:
        tool_filter: Optional whitelist of server tool names to expose.
    """
    url = os.environ.get("SEMRUSH_MCP_URL")
    if not url:
        return None
    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import (
            StreamableHTTPConnectionParams,
        )
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    except Exception:
        return None

    headers = {}
    key = os.environ.get("SEMRUSH_MCP_API_KEY")
    if key:
        headers["X-API-Key"] = key

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=url, headers=headers),
        tool_filter=tool_filter,
    )


def semrush_status() -> dict:
    """Report whether the Semrush MCP is configured (a plain diagnostic tool)."""
    return {
        "status": "configured" if os.environ.get("SEMRUSH_MCP_URL") else "not_configured",
        "reason": None if os.environ.get("SEMRUSH_MCP_URL")
        else "Set SEMRUSH_MCP_URL (+ SEMRUSH_MCP_API_KEY) in app/.env to enable live "
        "keyword/backlink/competitor data.",
    }
