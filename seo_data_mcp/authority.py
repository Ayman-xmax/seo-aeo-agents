# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Our OWN domain authority — PageRank over the link graph we crawled.

This is the same mechanism Open PageRank / Ahrefs DR / Semrush AS use (PageRank /
centrality over a web link graph, log-normalized to 0-100) — except the graph is
ours (built by crawl_links) and the computation is local. No third-party API, no fee.

Scale/coverage grows as you crawl more pages (or later, by ingesting the free
Common Crawl domain graph into the same `edges` table).
"""

from __future__ import annotations

import math
from collections import defaultdict

from . import store


def compute_pagerank(damping: float = 0.85, iterations: int = 40) -> dict:
    """Run PageRank over the accumulated edge graph; save 0-100 authority scores.

    Returns a summary (nodes, edges, top domains).
    """
    edges = store.all_edges()
    if not edges:
        return {"status": "empty", "reason": "No links crawled yet — run crawl_links first."}

    out_links: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for src, dst in edges:
        out_links[src].append(dst)
        nodes.add(src)
        nodes.add(dst)

    n = len(nodes)
    pr = dict.fromkeys(nodes, 1.0 / n)
    dangling = [node for node in nodes if not out_links.get(node)]

    for _ in range(iterations):
        dangling_share = damping * sum(pr[d] for d in dangling) / n
        base = (1.0 - damping) / n + dangling_share
        new_pr = dict.fromkeys(nodes, base)
        for src, outs in out_links.items():
            share = damping * pr[src] / len(outs)
            for dst in outs:
                new_pr[dst] += share
        pr = new_pr

    # Log-normalize to 0-100 (authority metrics are logarithmic, like DR/AS).
    max_pr = max(pr.values())
    ranked = sorted(pr.items(), key=lambda kv: kv[1], reverse=True)
    for rank, (domain, value) in enumerate(ranked, start=1):
        score = 0.0 if max_pr <= 0 else round(
            math.log1p(value) / math.log1p(max_pr) * 100, 1
        )
        store.upsert_authority(domain, score, rank)

    return {"status": "success", "nodes": n, "edges": len(edges),
            "top_domains": [{"domain": d, "authority_0_100":
                             round(math.log1p(v) / math.log1p(max_pr) * 100, 1)}
                            for d, v in ranked[:10]]}
