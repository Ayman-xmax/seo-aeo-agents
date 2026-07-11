# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""RAG retrieval over the curated SEO/AEO knowledge corpus (Layer 2).

Local, dependency-light vector store (numpy cosine) for the prototype; the same
`retrieve_knowledge` interface swaps to Vertex AI Search on deploy. Returns
`knowledge_base_empty` until `python -m app.knowledge_base.ingest` has run, so
agents never pretend to have guidance they don't.
"""

from __future__ import annotations

import json
import os

from .. import config

_INDEX_PATH = os.path.join(config.VECTOR_STORE_DIR, "index.json")


def _embed_query(text: str):
    """Embed a query string via google-genai; returns list[float] or None."""
    try:
        from google import genai

        client = genai.Client()
        resp = client.models.embed_content(model=config.EMBED_MODEL, contents=text)
        emb = resp.embeddings[0]
        return list(getattr(emb, "values", emb))
    except Exception:
        return None


def retrieve_knowledge(query: str, top_k: int) -> dict:
    """Retrieve the most relevant SEO/AEO best-practice passages for a query.

    Every result carries its source document so recommendations can cite it.

    Args:
        query: Natural-language question, e.g. 'how to fix crawled-not-indexed'.
        top_k: Number of passages to return (1-8 recommended).
    """
    if not os.path.exists(_INDEX_PATH):
        return {"status": "knowledge_base_empty",
                "reason": "Run `python -m app.knowledge_base.ingest` to seed the corpus."}
    try:
        import numpy as np
    except Exception:
        return {"status": "unavailable", "reason": "numpy not installed."}

    with open(_INDEX_PATH, encoding="utf-8") as f:
        index = json.load(f)
    chunks = index.get("chunks", [])
    if not chunks:
        return {"status": "knowledge_base_empty", "reason": "Index has no chunks."}

    q = _embed_query(query)
    if q is None:
        return {"status": "unavailable",
                "reason": "Embedding failed (check GOOGLE_API_KEY)."}

    mat = np.array([c["embedding"] for c in chunks], dtype="float32")
    qv = np.array(q, dtype="float32")
    denom = (np.linalg.norm(mat, axis=1) * np.linalg.norm(qv)) + 1e-9
    sims = (mat @ qv) / denom
    k = max(1, min(int(top_k), len(chunks)))
    top = sims.argsort()[::-1][:k]
    results = [
        {"source": chunks[i]["source"], "score": round(float(sims[i]), 4),
         "text": chunks[i]["text"]}
        for i in top
    ]
    return {"status": "success", "query": query, "results": results}
