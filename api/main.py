# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""FastAPI backend for the SEO/AEO agent web app.

Drives the ADK agent with a Runner + in-memory sessions and exposes:
  POST /api/session          -> create a session
  POST /api/chat             -> send a message, stream agent events as SSE
  GET  /api/state/{sid}      -> phase, brief, scorecard, action plan, change log
  GET  /api/health

Run:
    uv run uvicorn api.main:api --reload --port 8080
The React dev server (vite, :5173) proxies /api -> here, so there are no CORS issues.
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

# Importing app loads .env first (see app/__init__.py) and builds the agent tree.
from app.agent import app as adk_app
from app.observability import traceable

USER_ID = "web"

session_service = InMemorySessionService()
runner = Runner(
    app=adk_app,
    session_service=session_service,
    artifact_service=InMemoryArtifactService(),
)

api = FastAPI(title="SEO + AEO Agent API", version="1.0.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    session_id: str
    message: str


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@api.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "agent": adk_app.name}


@api.post("/api/session")
async def create_session() -> dict:
    sid = uuid.uuid4().hex[:12]
    await session_service.create_session(
        app_name=adk_app.name, user_id=USER_ID, session_id=sid
    )
    return {"session_id": sid}


@traceable(run_type="chain", name="seo_agent_run")
async def _drive(session_id: str, message: str):
    """Drive the agent for one message, yielding parsed event dicts. Decorated with
    @traceable so the ENTIRE run (every tool call + sub-agent + LLM call) is one nested
    trace in LangSmith — no LangChain involved. No-op without LANGSMITH_API_KEY."""
    msg = types.Content(role="user", parts=[types.Part(text=message)])
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=msg
    ):
        author = getattr(event, "author", "agent")
        for call in event.get_function_calls() or []:
            yield {"type": "tool_call", "agent": author, "tool": call.name}
        for resp in event.get_function_responses() or []:
            status = (resp.response or {}).get("status") if isinstance(
                resp.response, dict) else None
            yield {"type": "tool_result", "agent": author, "tool": resp.name,
                   "status": status}
        if event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            if text.strip():
                yield {"type": "message", "agent": author, "text": text,
                       "final": bool(event.is_final_response())}


@api.post("/api/chat")
async def chat(body: ChatIn) -> StreamingResponse:
    """Stream the agent's work (tool calls, messages) back as Server-Sent Events."""

    async def gen():
        try:
            async for ev in _drive(body.session_id, body.message):
                yield _sse(ev)
            yield _sse({"type": "done"})
        except Exception as e:  # surface errors to the UI instead of a dead stream
            yield _sse({"type": "error", "message": str(e)[:600]})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api.get("/api/state/{session_id}")
async def get_state(session_id: str) -> dict:
    """Everything the UI renders: brief, scorecard, action plan, change log."""
    session = await session_service.get_session(
        app_name=adk_app.name, user_id=USER_ID, session_id=session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    st = session.state
    scorecard = st.get("scorecard_baseline")
    return {
        "phase": st.get("phase"),
        "project_brief": st.get("project_brief"),
        "scorecard_baseline": scorecard if isinstance(scorecard, dict) else None,
        "scorecard_after": st.get("scorecard_after")
        if isinstance(st.get("scorecard_after"), dict) else None,
        "action_plan": st.get("action_plan"),
        "change_log": st.get("change_log") or [],
        "site_repo_path": st.get("site_repo_path"),
        "site_type": st.get("site_type"),
        "page_inventory": st.get("page_inventory") or [],
        "gsc_baseline": st.get("gsc_baseline"),  # real rankings/clicks baseline (if GSC set)
        "publish_approved": bool(st.get("publish_approved")),
    }


# Serve the built React app from the same container (single-container deploy). The /api/*
# routes above are matched first; this catch-all serves the SPA + its assets.
_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(_DIST):
    from fastapi.staticfiles import StaticFiles

    api.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")
