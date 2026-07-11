# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Provider-aware embeddings (Google Gemini or OpenAI).

Single entry point used by both the RAG ingester and the retrieval tool, so the
same model is always used for indexing and querying. Returns None on failure so
callers degrade gracefully instead of crashing.
"""

from __future__ import annotations

from . import config


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a list of texts with the configured provider/model."""
    if not texts:
        return []
    if config.EMBED_PROVIDER == "openai":
        try:
            from openai import OpenAI

            client = OpenAI()
            resp = client.embeddings.create(model=config.EMBED_MODEL, input=texts)
            return [d.embedding for d in resp.data]
        except Exception as e:  # pragma: no cover
            print(f"[embeddings] OpenAI embed failed: {e}")
            return None
    # default: Google Gemini
    try:
        from google import genai

        client = genai.Client()
        out: list[list[float]] = []
        for t in texts:
            resp = client.models.embed_content(model=config.EMBED_MODEL, contents=t)
            emb = resp.embeddings[0]
            out.append(list(getattr(emb, "values", emb)))
        return out
    except Exception as e:  # pragma: no cover
        print(f"[embeddings] Gemini embed failed: {e}")
        return None
