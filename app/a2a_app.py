# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Expose the SEO/AEO agent over the A2A (Agent2Agent) protocol.

This makes the whole 3-phase system callable by *other* agents as a standard A2A
service: ADK builds an Agent Card from the root agent (name, description, and its
sub-agent skills) and serves the A2A JSON-RPC endpoints.

Run:
    uv run uvicorn app.a2a_app:a2a_app --host 0.0.0.0 --port 8001

Then the card is discoverable at:
    http://localhost:8001/.well-known/agent-card.json

Consume it from another ADK agent with:
    from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
    seo = RemoteA2aAgent(
        name="seo_agent",
        agent_card="http://localhost:8001/.well-known/agent-card.json",
    )
"""

from __future__ import annotations

import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import root_agent

_HOST = os.environ.get("A2A_HOST", "localhost")
_PORT = int(os.environ.get("A2A_PORT", "8001"))

# Starlette ASGI app implementing the A2A protocol for this agent.
a2a_app = to_a2a(root_agent, host=_HOST, port=_PORT)
