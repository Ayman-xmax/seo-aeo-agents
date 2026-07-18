# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Run the eval suite against the CURRENT model config and grade every case.

Usage:
    # grade the model your .env selects:
    uv run python -m eval.run_eval

    # try a specific model without editing .env:
    SEO_LLM_PROVIDER=openai SEO_WORKER_MODEL=openai/gpt-4o-mini \
        uv run python -m eval.run_eval --tag gpt-4o-mini

    # compare two report files:
    uv run python -m eval.run_eval --compare eval/results/A.json eval/results/B.json

Writes a JSON report to eval/results/<tag>.json and prints a per-dimension table so you
can see, per model, where it is FAILING / NOT DOING IT / LACKING / mishandling the objective.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

# app/__init__ loads .env before config reads it.
from app import config
from app.agent import app as adk_app
from eval.graders import grade_run

_HERE = os.path.dirname(__file__)
_RESULTS = os.path.join(_HERE, "results")


def _load_cases() -> list[dict]:
    import yaml
    with open(os.path.join(_HERE, "cases.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f).get("cases", [])


async def _run_case(case: dict) -> tuple[list[dict], dict]:
    """Run one case through the agent; return (trace, final_state)."""
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    sessions = InMemorySessionService()
    runner = Runner(app=adk_app, session_service=sessions,
                    artifact_service=InMemoryArtifactService())
    sid = "eval_" + case["id"]
    await sessions.create_session(app_name=adk_app.name, user_id="eval", session_id=sid)

    trace: list[dict] = []
    msg = types.Content(role="user", parts=[types.Part(text=case["prompt"])])
    try:
        async for event in runner.run_async(user_id="eval", session_id=sid, new_message=msg):
            author = getattr(event, "author", "agent")
            for call in event.get_function_calls() or []:
                trace.append({"type": "tool_call", "agent": author, "tool": call.name})
            for resp in event.get_function_responses() or []:
                status = (resp.response or {}).get("status") if isinstance(
                    resp.response, dict) else None
                trace.append({"type": "tool_result", "agent": author,
                              "tool": resp.name, "status": status})
            if event.content and event.content.parts:
                text = "".join(p.text or "" for p in event.content.parts)
                if text.strip():
                    trace.append({"type": "message", "agent": author, "text": text,
                                  "final": bool(event.is_final_response())})
    except Exception as e:
        trace.append({"type": "error", "message": str(e)[:400]})

    session = await sessions.get_session(app_name=adk_app.name, user_id="eval", session_id=sid)
    return trace, (session.state if session else {})


async def _run_suite(tag: str) -> dict:
    cases = _load_cases()
    model_tag = tag or f"{config.LLM_PROVIDER}:{config.WORKER_MODEL}"
    print(f"[eval] model = {model_tag} | {len(cases)} cases\n")
    graded = []
    for case in cases:
        t0 = time.time()
        trace, state = await _run_case(case)
        g = grade_run(trace, state)
        g["case"] = case["id"]
        g["seconds"] = round(time.time() - t0, 1)
        graded.append(g)
        print(f"  {case['id']:16s} overall={g['overall']:.2f} "
              f"tools={g['metrics']['tool_calls']} errs={g['metrics']['errors']} "
              f"{g['seconds']}s")
    return {"model": model_tag, "cases": graded,
            "overall": round(sum(c["overall"] for c in graded) / len(graded), 3)
            if graded else 0.0}


def _print_dimensions(report: dict) -> None:
    dims: dict[str, list[float]] = {}
    for c in report["cases"]:
        for r in c["results"]:
            dims.setdefault(r["dimension"], []).append(r["score"])
    print(f"\n=== {report['model']} — overall {report['overall']:.2f} ===")
    print("  by dimension (where the model stands):")
    for dim, scores in sorted(dims.items()):
        avg = sum(scores) / len(scores)
        flag = "OK " if avg >= 0.8 else "!! " if avg < 0.5 else "~  "
        print(f"    {flag}{dim:18s} {avg:.2f}")
    # surface concrete weak spots
    print("  weak spots:")
    weak = [(c["case"], r["grader"], r["detail"])
            for c in report["cases"] for r in c["results"] if r["score"] < 0.999]
    for case, grader, detail in weak[:20]:
        print(f"    - [{case}] {grader}: {detail}")
    if not weak:
        print("    (none — all graders passed)")


def _compare(a_path: str, b_path: str) -> None:
    a = json.load(open(a_path, encoding="utf-8"))
    b = json.load(open(b_path, encoding="utf-8"))
    print(f"\n=== COMPARE: {a['model']} ({a['overall']:.2f}) vs "
          f"{b['model']} ({b['overall']:.2f}) ===")
    for rep in (a, b):
        _print_dimensions(rep)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="label for this model run")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="compare two existing report JSONs")
    args = ap.parse_args()

    if args.compare:
        _compare(*args.compare)
        return 0

    report = asyncio.run(_run_suite(args.tag))
    _print_dimensions(report)
    os.makedirs(_RESULTS, exist_ok=True)
    tag = (args.tag or report["model"]).replace("/", "_").replace(":", "_")
    out = os.path.join(_RESULTS, f"{tag}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[eval] report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
