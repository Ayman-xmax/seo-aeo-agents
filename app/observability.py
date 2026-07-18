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


def enable_langsmith() -> bool:
    """Register the LiteLLM->LangSmith callback if a key is present. Safe no-op otherwise."""
    if not (os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")):
        return False
    try:
        import litellm

        current = list(getattr(litellm, "callbacks", []) or [])
        if "langsmith" not in current:
            current.append("langsmith")
            litellm.callbacks = current
        os.environ.setdefault("LANGSMITH_PROJECT", "seo-aeo-agent")
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        return True
    except Exception:
        return False
