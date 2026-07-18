# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""CI quality gate — run the live eval suite and fail if the score regresses.

Runs the current model over eval/cases.yaml (real Phase-1 runs) and exits non-zero if
the overall score is below SEO_EVAL_MIN_SCORE (default 0.6). Used by the eval-gate CI
job when an LLM key is present; skipped otherwise.

    SEO_EVAL_MIN_SCORE=0.7 uv run python -m eval.gate
"""

from __future__ import annotations

import asyncio
import os
import sys

from eval.run_eval import _print_dimensions, _run_suite


def main() -> int:
    threshold = float(os.environ.get("SEO_EVAL_MIN_SCORE", "0.6"))
    report = asyncio.run(_run_suite(os.environ.get("SEO_EVAL_TAG", "")))
    _print_dimensions(report)
    print(f"\n[gate] overall={report['overall']:.3f}  threshold={threshold}")
    if report["overall"] < threshold:
        print("[gate] FAIL — model quality regressed below threshold")
        return 1
    print("[gate] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
