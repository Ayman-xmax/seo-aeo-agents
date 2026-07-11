# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Build the local RAG index from the curated corpus.

Run:  uv run python -m app.knowledge_base.ingest

Reads app/knowledge/*.md|*.txt, chunks semantically (~1800 chars, header-aware),
embeds each chunk with text-embedding-004, and writes the vector store to
app/knowledge_base/vector_store/index.json. Swap this for a Vertex AI Search
datastore on deploy without changing the retrieval interface.
"""

from __future__ import annotations

import glob
import json
import os
import re

from .. import config
from ..embeddings import embed_texts

# Standalone scripts don't get the ADK runtime's .env loading — do it ourselves.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))
except Exception:
    pass


def _chunk(text: str, target: int, overlap: int) -> list[str]:
    """Header-aware chunking: split on markdown headings, then pack to ~target chars."""
    blocks = re.split(r"(?m)^(?=#{1,6}\s)", text)
    chunks: list[str] = []
    buf = ""
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(buf) + len(block) + 1 <= target:
            buf = f"{buf}\n{block}".strip()
        else:
            if buf:
                chunks.append(buf)
            if len(block) <= target:
                buf = block
            else:  # very long block -> hard-split with overlap
                for i in range(0, len(block), target - overlap):
                    chunks.append(block[i:i + target])
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


def main() -> int:
    corpus = sorted(
        glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md"))
        + glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.txt"))
    )
    corpus = [p for p in corpus if os.path.basename(p).lower() != "readme.md"]
    if not corpus:
        print(f"[ingest] No corpus files in {config.KNOWLEDGE_DIR}. Add .md/.txt docs first.")
        return 1

    records: list[dict] = []
    for path in corpus:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        source = os.path.basename(path)
        for chunk in _chunk(text, config.CHUNK_TARGET_CHARS, config.CHUNK_OVERLAP_CHARS):
            records.append({"source": source, "text": chunk})

    print(f"[ingest] {len(corpus)} docs -> {len(records)} chunks. "
          f"Embedding with {config.EMBED_PROVIDER}:{config.EMBED_MODEL} ...")
    embeddings = embed_texts([r["text"] for r in records])
    if embeddings is None:
        print("[ingest] Aborting -- check the API key for your provider in app/.env.")
        return 1
    for r, e in zip(records, embeddings, strict=False):
        r["embedding"] = e

    os.makedirs(config.VECTOR_STORE_DIR, exist_ok=True)
    out_path = os.path.join(config.VECTOR_STORE_DIR, "index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": config.EMBED_MODEL, "chunks": records}, f)
    print(f"[ingest] Wrote {len(records)} chunks -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
