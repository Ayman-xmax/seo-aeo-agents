# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""GCP-free local runner for AI Studio (API-key) mode.

The scaffold's fast_api_app.py requires GCP credentials (google.auth.default,
Cloud Logging), so `agents-cli run/playground` won't start without a GCP project.
This runner drives the agent with an in-memory session and prints a readable
trace — the right tool for local prototyping on an AI Studio key.

    uv run python -m app.run_local "Analyze https://example.com for the X niche"
"""

from __future__ import annotations

import asyncio
import os
import sys
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from app.agent import app as adk_app  # noqa: E402

USER_ID = "local"
SESSION_ID = "smoke"


def _fmt(text: str, limit: int = 600) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + " …"


async def main(prompt: str) -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )
    await session_service.create_session(
        app_name=adk_app.name, user_id=USER_ID, session_id=SESSION_ID
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    print(f"\n=== RUN: {_fmt(prompt, 200)}\n")
    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=msg
    ):
        author = getattr(event, "author", "?")
        for call in event.get_function_calls() or []:
            args = {k: _fmt(str(v), 80) for k, v in (call.args or {}).items()}
            print(f"  [{author}] -> tool {call.name}({args})")
        for resp in event.get_function_responses() or []:
            status = ""
            if isinstance(resp.response, dict):
                status = resp.response.get("status", "")
            print(f"  [{author}] <- {resp.name} {status}")
        if event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            if text.strip():
                tag = "FINAL" if event.is_final_response() else "say"
                print(f"  [{author}] {tag}: {_fmt(text)}")

    # Dump the deterministic scorecard if Phase 1 produced one.
    session = await session_service.get_session(
        app_name=adk_app.name, user_id=USER_ID, session_id=SESSION_ID
    )
    sc = session.state.get("scorecard_baseline")
    if sc:
        print(f"\n=== BASELINE SCORE: overall={sc.get('overall')} coverage={sc.get('coverage')}")
        for c in sc.get("categories", []):
            print(f"      {c['category']}: {c['score']}")


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "The niche is 'domain landing pages' and the target site is https://example.com. "
        "Set the project brief and run the Phase 1 read-only diagnosis now; I approve the analysis."
    )
    asyncio.run(main(prompt))
