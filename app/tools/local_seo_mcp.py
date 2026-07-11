# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Connect the agents to the local free-data FastMCP server (seo_data_mcp).

Launches it as a stdio subprocess with the SAME interpreter (so mcp/requests are
available). Returns None if disabled or unavailable, so the tree still builds.
Disable with SEO_DISABLE_LOCAL_MCP=1.
"""

from __future__ import annotations

import os
import sys

# seo-agent/ project root (parent of the app package).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_local_seo_mcp():
    """Return an McpToolset for the free-data server, or None."""
    if os.environ.get("SEO_DISABLE_LOCAL_MCP"):
        return None
    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import (
            StdioConnectionParams,
            StdioServerParameters,
        )
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    except Exception:
        return None
    try:
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "seo_data_mcp.server"],
                    cwd=_PROJECT_ROOT,
                ),
                timeout=60.0,
            ),
        )
    except Exception:
        return None
