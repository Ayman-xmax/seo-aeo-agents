# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Bridge: expose this ADK SEO/AEO system to LangChain DeepAgents as a tool.

Rationale: our system is already a deep multi-agent planner (ADK). Rather than rebuild
it in LangChain, we expose it as a single high-level LangChain tool so a LangChain
DeepAgent can call `seo_audit(url)` as one capability in a larger workflow.

Install the optional stack first:
    uv sync --extra langchain

Then:
    from integrations.langchain_bridge import build_seo_deepagent
    agent = build_seo_deepagent()   # a deepagents agent with our seo_audit tool
    agent.invoke({"messages": [{"role": "user",
                                "content": "Audit https://example.com and summarize."}]})
"""

from __future__ import annotations

import asyncio


def run_seo_phase1(url: str) -> dict:
    """Run our ADK agent's Phase-1 diagnosis for a URL and return score + plan.

    Pure-Python entry point (no LangChain needed) — also handy for scripts/tests.
    """
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from app.agent import app as adk_app
    from app.observability import traceable

    @traceable(run_type="chain", name="seo_phase1")
    async def _go() -> dict:
        sessions = InMemorySessionService()
        runner = Runner(app=adk_app, session_service=sessions,
                        artifact_service=InMemoryArtifactService())
        sid = "lc_bridge"
        await sessions.create_session(app_name=adk_app.name, user_id="lc", session_id=sid)
        prompt = f"Analyze {url} and run the Phase 1 diagnosis. I approve the analysis."
        msg = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for _ in runner.run_async(user_id="lc", session_id=sid, new_message=msg):
            pass
        session = await sessions.get_session(app_name=adk_app.name, user_id="lc",
                                             session_id=sid)
        st = session.state if session else {}
        return {
            "niche": (st.get("project_brief") or {}).get("niche"),
            "scorecard": st.get("scorecard_baseline"),
            "action_plan": st.get("action_plan"),
        }

    return asyncio.run(_go())


def seo_audit_tool():
    """Return a LangChain StructuredTool wrapping our Phase-1 audit. Requires langchain."""
    try:
        from langchain_core.tools import tool
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "langchain not installed. Run: uv sync --extra langchain"
        ) from e

    @tool
    def seo_audit(url: str) -> str:
        """Run a full SEO/AEO audit of a website and return its Health Score and a
        concrete action plan. Input: the site URL."""
        r = run_seo_phase1(url)
        sc = r.get("scorecard") or {}
        return (
            f"Niche: {r.get('niche')}\n"
            f"Overall Health Score: {sc.get('overall')} (coverage {sc.get('coverage')})\n\n"
            f"Action plan:\n{r.get('action_plan') or '(none)'}"
        )

    return seo_audit


def build_seo_deepagent(model: str = "gpt-4o-mini"):
    """Build a LangChain DeepAgent that can call our SEO system as a tool.

    Requires the optional stack: uv sync --extra langchain (+ OPENAI_API_KEY).
    """
    try:
        from deepagents import create_deep_agent
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "deepagents not installed. Run: uv sync --extra langchain"
        ) from e

    instructions = (
        "You are an SEO strategist. Use the seo_audit tool to analyze any website the "
        "user gives you, then explain the findings and prioritized fixes in plain language."
    )
    return create_deep_agent(tools=[seo_audit_tool()], instructions=instructions,
                             model=model)
