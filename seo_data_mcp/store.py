# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Our OWN accumulating SEO index (SQLite).

This is the ownership core: every keyword we expand and every SERP we fetch is
persisted here, so over time we build a proprietary keyword/SERP/authority
dataset — the thing Semrush charges a subscription for — for free and owned by us.
"""

from __future__ import annotations

import datetime
import os
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(__file__), "seo_index.db")


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS keywords (
            keyword TEXT, market TEXT, source TEXT, first_seen TEXT,
            PRIMARY KEY (keyword, market)
        );
        CREATE TABLE IF NOT EXISTS serp (
            query TEXT, market TEXT, rank INTEGER, domain TEXT, url TEXT, seen TEXT,
            PRIMARY KEY (query, market, rank)
        );
        CREATE TABLE IF NOT EXISTS authority (
            domain TEXT PRIMARY KEY, score REAL, rank INTEGER, updated TEXT
        );
        CREATE TABLE IF NOT EXISTS edges (
            src TEXT, dst TEXT, first_seen TEXT, PRIMARY KEY (src, dst)
        );
        CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
        """
    )
    return conn


def add_edges(src: str, dsts: list[str]) -> int:
    """Record src-domain -> dst-domain hyperlinks in our owned link graph."""
    dsts = [d for d in {d.strip() for d in dsts} if d and d != src]
    if not src or not dsts:
        return 0
    conn = connect()
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO edges(src, dst, first_seen) VALUES (?,?,?)",
            [(src, d, _now()) for d in dsts],
        )
    conn.close()
    return len(dsts)


def all_edges() -> list[tuple[str, str]]:
    conn = connect()
    rows = conn.execute("SELECT src, dst FROM edges").fetchall()
    conn.close()
    return rows


def referring_domains(domain: str, limit: int) -> list[str]:
    """Domains that link TO `domain` = the backlinks we've discovered (incoming edges)."""
    conn = connect()
    rows = conn.execute(
        "SELECT DISTINCT src FROM edges WHERE dst=? LIMIT ?", (domain, limit)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def upsert_keywords(keywords: list[str], market: str, source: str) -> int:
    if not keywords:
        return 0
    conn = connect()
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO keywords(keyword, market, source, first_seen) "
            "VALUES (?,?,?,?)",
            [(k, market, source, _now()) for k in keywords],
        )
    n = conn.total_changes
    conn.close()
    return n


def record_serp(query: str, market: str, rows: list[dict]) -> int:
    """rows: [{rank, domain, url}]. Accumulates our own SERP index."""
    if not rows:
        return 0
    conn = connect()
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO serp(query, market, rank, domain, url, seen) "
            "VALUES (?,?,?,?,?,?)",
            [(query, market, r["rank"], r["domain"], r.get("url", ""), _now())
             for r in rows],
        )
    conn.close()
    return len(rows)


def upsert_authority(domain: str, score: float, rank: int) -> None:
    conn = connect()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO authority(domain, score, rank, updated) "
            "VALUES (?,?,?,?)",
            (domain, score, rank, _now()),
        )
    conn.close()


def get_authority(domain: str) -> dict | None:
    conn = connect()
    row = conn.execute(
        "SELECT domain, score, rank, updated FROM authority WHERE domain=?", (domain,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"domain": row[0], "score": row[1], "rank": row[2], "updated": row[3]}


def competitors_from_index(market: str, limit: int) -> list[dict]:
    """Domains that recur most across our accumulated SERP index = SEO competitors."""
    conn = connect()
    rows = conn.execute(
        "SELECT domain, COUNT(DISTINCT query) AS q FROM serp WHERE market=? "
        "GROUP BY domain ORDER BY q DESC LIMIT ?",
        (market, limit),
    ).fetchall()
    conn.close()
    return [{"domain": d, "ranking_queries": q} for d, q in rows]


def stats() -> dict:
    conn = connect()
    kw = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
    serp = conn.execute("SELECT COUNT(*) FROM serp").fetchone()[0]
    dom = conn.execute("SELECT COUNT(*) FROM authority").fetchone()[0]
    edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    conn.close()
    return {"keywords_indexed": kw, "serp_rows": serp, "domains_scored": dom,
            "link_edges": edges, "db_path": _DB_PATH}
