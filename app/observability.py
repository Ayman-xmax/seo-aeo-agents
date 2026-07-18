# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Optional LangSmith tracing.

When LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) is set, we register LiteLLM's LangSmith
callback so every LLM call on the OpenAI/LiteLLM path is traced in LangSmith (prompt,
response, latency, tokens) — useful for eval and debugging.

Honest boundary: this traces the LiteLLM path (SEO_LLM_PROVIDER=openai). Gemini is
native to ADK and emits OpenTelemetry (Cloud Trace), not LangSmith — so for full-stack
tracing in LangSmith, run on the OpenAI provider.
"""

from __future__ import annotations

import os


def _noop_traceable(*d_args, **d_kwargs):
    """Fallback so @traceable works even if langsmith is missing. Supports both
    @traceable and @traceable(...) forms."""
    if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
        return d_args[0]

    def deco(fn):
        return fn

    return deco


# Real langsmith `traceable` when available (it's a near-passthrough when tracing is
# disabled, so decorating is always safe); otherwise a no-op.
try:
    from langsmith import traceable
except Exception:  # pragma: no cover
    traceable = _noop_traceable


def enable_langsmith() -> bool:
    """Enable LangSmith tracing if a key is present. Safe no-op otherwise.

    Primary: native ADK tracing via OpenTelemetry (langsmith[google-adk]) — captures the
    WHOLE agent tree (Gemini + OpenAI). Fallback: the LiteLLM callback (OpenAI path only).
    """
    if not (os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")):
        return False
    os.environ.setdefault("LANGSMITH_PROJECT", "seo-aeo-agent")
    os.environ.setdefault("LANGSMITH_TRACING", "true")

    # Native ADK -> LangSmith via OpenTelemetry (best: full agent tree, all providers).
    try:
        from langsmith.integrations.otel import configure

        configure()
        return True
    except Exception:
        pass

    # Fallback: LiteLLM callback (traces LLM calls on the OpenAI path only).
    try:
        import litellm

        current = list(getattr(litellm, "callbacks", []) or [])
        if "langsmith" not in current:
            current.append("langsmith")
            litellm.callbacks = current
        return True
    except Exception:
        return False
