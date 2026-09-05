"""GitHub issue polling (v2 §6.2): `orch watch` -> FIFO sequential processing.

- `gh issue list --label orch --state open` every interval (default 60s).
- One task at a time, oldest first (FIFO; v2 §7.1 forbids concurrency).
- A start comment `🔧 orch가 작업을 시작했습니다 (task: <task_id>)` claims the
  issue; later polls skip claimed issues (idempotency).
- `orch-retry` label on an orch-labeled issue: re-inject as a retry
  (checkpoint values merged so attempt/fix_attempt continue; v2 §7.7), then the
  label is removed after the run.
"""

import json
import re
import time
from datetime import datetime

from . import graph as graph_mod
from . import lock, runners
from .cli import _initial_state, _run_graph, get_checkpoint_tuple
from .state import TaskState

ORCH_LABEL = "orch"
RETRY_LABEL = "orch-retry"
CLAIM_MARKER = "orch가 작업을 시작했습니다"
PR_MARKER = "orch created a PR"
FAILED_PREFIX = "orch task failed:"


def _log(msg: str) -> None:
    print(f"[orch/watch] {msg}", flush=True)


def _fetch_orch_issues(repo: str) -> list[dict]:
    res = runners.gh("issue", "list", "--label", ORCH_LABEL, "--state", "open",
                     "--json", "number,title,body,createdAt",
                     "-q", "sort_by(.createdAt) | .[]", repo_path=repo)
    if not res["ok"]:
        _log(f"gh issue list failed: {res['error']}")
        return []
    items = []
    for line in res["stdout"].splitlines():
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except ValueError:
                pass
    items.sort(key=lambda i: i.get("createdAt") or "")
    return items


def _has_marker(repo: str, issue_no: int, needle: str) -> bool:
    res = runners.gh("issue", "view", str(issue_no), "--json", "comments",
                     "-q", '[.comments[].body] | join("\\n")', repo_path=repo)
    return res["ok"] and needle in (res["stdout"] or "")


def _has_label(repo: str, issue_no: int, label: str) -> bool:
    res = runners.gh("issue", "view", str(issue_no), "--json", "labels",
                     "-q", '[.labels[].name]', repo_path=repo)
    if not res["ok"]:
        return False
    try:
        return label in json.loads(res["stdout"] or "[]")
    except ValueError:
        return False


def _remove_label(repo: str, issue_no: int, label: str) -> None:
    runners.gh("issue", "edit", str(issue_no), "--remove-label", label, repo_path=repo)


def _claim(repo: str, issue_no: int, task_id: str) -> bool:
    """Post the start comment; False if an earlier claim beat us (race-safe)."""
    if _has_marker(repo, issue_no, CLAIM_MARKER):
        return False
    body = f"🔧 {CLAIM_MARKER} (task: {task_id})"
    res = runners.gh("issue", "comment", str(issue_no), "--body", body, repo_path=repo)
    return res["ok"]


def _extract_retry_task_id(body: str) -> str | None:
    """From a start comment body like '... (task: gh-123)...' return gh-123."""
    m = re.search(r"\(task:\s*([A-Za-z0-9\-]+)\)", body or "")
    return m.group(1) if m else None


def _process_issue(repo: str, issue: dict) -> None:
    issue_no = issue["number"]
    task_id = f"gh-{issue_no}"
    if _has_label(repo, issue_no, RETRY_LABEL):
        task_id = _retry_task_id(repo, issue_no) or task_id
        retry = True
    else:
        retry = False

    # Lock FIRST (v2 §7.1: on lock failure the issue stays unclaimed and is
    # retried on the next poll — no progress comment is left behind).
    lm = lock.LockManager(repo, task_id, log=_log)
    try:
        lm.__enter__()
    except lock.LockUnavailable as e:
        _log(f"issue #{issue_no} deferred (repo busy): {e}")
        return

    try:
        if not _claim(repo, issue_no, task_id):
            _log(f"issue #{issue_no}: already claimed, skipping")
            return

        _log(f"issue #{issue_no} -> task {task_id} ({'retry' if retry else 'new'})")

        body = (issue.get("body") or "").strip() or issue.get("title", "").strip()
        state = _initial_state(task_id, "github", repo, body, issue_no=issue_no)

        if retry:
            saved = get_checkpoint_tuple(repo, task_id)
            if saved and saved.checkpoint:
                vals = dict(saved.checkpoint.get("channel_values", {}))
                state = TaskState(**{**state, **{k: vals[k] for k in vals if k in state}})
                state["failure_reason"] = None
                state["status"] = "running"

        final = _run_graph(state)
        _log(f"task {task_id}: {final.get('status')}"
             + (f" pr={final.get('pr_url')}" if final.get("pr_url") else "")
             + (f" reason={final.get('failure_reason')}" if final.get("failure_reason") else ""))
    except lock.LockUnavailable as e:
        _log(f"task {task_id} deferred: {e}")
    finally:
        lm.__exit__(None, None, None)
        if _has_label(repo, issue_no, RETRY_LABEL):
            _remove_label(repo, issue_no, RETRY_LABEL)  # v2 §7.7 remove after processing


def _retry_task_id(repo: str, issue_no: int) -> str | None:
    """Find the original task id from the claim comment."""
    res = runners.gh("issue", "view", str(issue_no), "--json", "comments",
                     "-q", '[.comments[].body] | join("\\n==\\n")', repo_path=repo)
    if not res["ok"]:
        return None
    for chunk in (res["stdout"] or "").split("=="):
        if CLAIM_MARKER in chunk:
            return _extract_retry_task_id(chunk)
    return None


def watch_loop(repo: str, interval_s: int = 60, stop=None) -> int:
    """stop: optional threading.Event — set() breaks the loop (dashboard use).
    None preserves classic Ctrl+C behavior."""
    _log(f"watching repo={repo} label={ORCH_LABEL} interval={interval_s}s (Ctrl+C to stop)")
    try:
        while True:
            for issue in _fetch_orch_issues(repo):
                if stop is not None and stop.is_set():
                    _log("stop requested")
                    return 0
                try:
                    _process_issue(repo, issue)
                except lock.LockUnavailable:
                    raise
                except Exception as exc:  # keep the loop alive on per-issue errors
                    _log(f"issue #{issue.get('number')} error: {exc}")
            if stop is not None:
                for _ in range(int(interval_s)):
                    if stop.is_set():
                        _log("stop requested")
                        return 0
                    time.sleep(1)
            else:
                time.sleep(interval_s)
    except KeyboardInterrupt:
        _log("stopped")
        return 0
