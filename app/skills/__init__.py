# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Per-agent skill playbooks.

Each `<agent_name>.md` here is a focused operating procedure (methodology, tool
order, quality checklist, efficiency tips, pitfalls) that is appended to that
agent's instruction at build time. This raises productivity/efficiency without
bloating the code, and lets you tune an agent's behaviour by editing one markdown
file — no code change.
"""

from __future__ import annotations

import functools
import os

_DIR = os.path.dirname(__file__)


@functools.cache
def load_skill(name: str) -> str:
    """Return the skill playbook text for `name`, or '' if none exists."""
    path = os.path.join(_DIR, f"{name}.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return ""
