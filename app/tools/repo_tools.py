# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License").
"""Provide the site's git repo directly in chat.

clone_site_repo pulls a repo URL into a local working copy and records its path in
session state, so Phase 2 edits the real files. commit_changes commits the applied
edits (git = rollback/review). Push stays manual (needs the user's git auth).
"""

from __future__ import annotations

import os
import re
import subprocess

from google.adk.tools.tool_context import ToolContext

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WORKDIR = os.path.join(_PROJECT_ROOT, ".site_repos")
# All edits land on this branch, never main — reviewed via PR before the user merges.
_BRANCH = "seo-agent-optimizations"


def _list_html(root: str, limit: int = 40) -> list[str]:
    out = []
    for dirpath, _dirs, files in os.walk(root):
        if ".git" in dirpath:
            continue
        for fn in files:
            if fn.endswith((".html", ".htm")):
                out.append(os.path.relpath(os.path.join(dirpath, fn), root))
                if len(out) >= limit:
                    return out
    return out


def clone_site_repo(repo_url: str, tool_context: ToolContext) -> dict:
    """Clone the site's git repo so Phase 2 can edit its real files.

    Public repos work directly; private repos need your git credentials configured on
    this machine. Records the local path in session state for the publisher to use.

    Args:
        repo_url: The git URL, e.g. 'https://github.com/you/your-site.git'.
    """
    name = re.sub(r"[^A-Za-z0-9_.-]", "_",
                  repo_url.rstrip("/").split("/")[-1].replace(".git", "")) or "site"
    os.makedirs(_WORKDIR, exist_ok=True)
    dest = os.path.join(_WORKDIR, name)
    try:
        if os.path.isdir(os.path.join(dest, ".git")):
            subprocess.run(["git", "-C", dest, "pull", "--ff-only"],
                           capture_output=True, text=True, timeout=120)
        else:
            r = subprocess.run(["git", "clone", "--depth", "1", repo_url, dest],
                               capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                return {"status": "error",
                        "reason": f"git clone failed: {r.stderr.strip()[:300]}. "
                        "For a private repo, ensure your git credentials are set up."}
    except Exception as e:
        return {"status": "error", "reason": f"clone failed: {e}"}

    # Work on a dedicated branch, never main.
    subprocess.run(["git", "-C", dest, "checkout", "-B", _BRANCH],
                   capture_output=True, text=True)
    tool_context.state["site_repo_path"] = dest
    htmls = _list_html(dest)
    return {"status": "success", "repo_path": dest, "branch": _BRANCH,
            "html_files_found": len(htmls), "sample_files": htmls[:15],
            "note": f"Repo ready on branch '{_BRANCH}'. Approved changes write to these files."}


def commit_changes(message: str, tool_context: ToolContext) -> dict:
    """Commit the applied edits in the cloned site repo (review/rollback via git).

    Push stays manual (needs your git auth). Blocked until approved (implement phase).

    Args:
        message: The commit message.
    """
    repo = tool_context.state.get("site_repo_path") or os.environ.get("SITE_REPO_PATH")
    if not repo:
        return {"status": "no_repo", "reason": "No site repo — call clone_site_repo first."}
    try:
        subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True, text=True)
        c = subprocess.run(["git", "-C", repo, "commit", "-m", message],
                           capture_output=True, text=True, timeout=60)
        if c.returncode != 0 and "nothing to commit" in (c.stdout + c.stderr).lower():
            return {"status": "nothing_to_commit"}
        stat = subprocess.run(["git", "-C", repo, "--no-pager", "show", "--stat",
                               "--oneline", "HEAD"], capture_output=True, text=True)
        return {"status": "committed", "branch": _BRANCH,
                "summary": stat.stdout.strip()[:1200],
                "note": f"Committed to branch '{_BRANCH}'. Use push_changes to push it for PR review."}
    except Exception as e:
        return {"status": "error", "reason": f"commit failed: {e}"}


def push_changes(tool_context: ToolContext) -> dict:
    """Push the optimizations branch to origin so the user can open a pull request.

    Needs the user's git write access (credential manager / token). Never touches main.
    """
    repo = tool_context.state.get("site_repo_path") or os.environ.get("SITE_REPO_PATH")
    if not repo:
        return {"status": "no_repo", "reason": "No site repo — call clone_site_repo first."}
    try:
        r = subprocess.run(["git", "-C", repo, "push", "-u", "origin", _BRANCH],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return {"status": "error", "reason": (r.stderr.strip() or r.stdout.strip())[:400],
                    "hint": "Push needs write access. Ensure your git credentials/token are "
                    "set up, or push manually: "
                    f"git -C \"{repo}\" push -u origin {_BRANCH}"}
        return {"status": "pushed", "branch": _BRANCH,
                "note": "Pushed. Open a pull request on your repo to review and merge, then "
                "deploy. Nothing is live until you merge."}
    except Exception as e:
        return {"status": "error", "reason": f"push failed: {e}"}
