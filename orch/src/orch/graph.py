"""langgraph graph: fetch_task -> analyze -> create_branch -> implement -> test
-> create_pr, with fix loop (fix -> test, v2 change #1) and fail_task sink.

Edge table (v2 §5 + handoff v2.1 overrides):

| From       | condition                                    | To                            |
|------------|----------------------------------------------|-------------------------------|
| fetch_task | ok                                           | analyze                       |
| fetch_task | lock failure surfaced in state               | fail_task(lock_unavailable)   |
| analyze    | ok, worktree unchanged (수정6)               | create_branch                 |
| analyze    | CLI failure / worktree changed               | fail_task(analyze_error)      |
| create_branch | ok                                       | implement                     |
| implement  | ok + diff non-empty                          | test                          |
| implement  | ok + diff EMPTY (수정5)                      | fail_task(no_changes)         |
| implement  | crash/timeout, attempt<3 (수정8)             | implement (attempt += 1)      |
| implement  | crash/timeout, attempt>=3                    | fail_task(implement_crash)    |
| implement  | secret detected in staged diff (v2 §7.3)     | fail_task(secret_detected)    |
| test       | detection failed (v2 §7.6)                   | fail_task(no_test_command)    |
| test       | passed                                       | review                        |
| test       | failed, fix_attempt<3                        | fix (fix += 1 on entry)       |
| test       | failed, fix_attempt>=3                       | fail_task(test_failed_exhausted) |
| fix        | done                                         | test (ALWAYS re-test)         |
| fix        | secret detected in staged diff (v2 §7.3)     | fail_task(secret_detected)    |
| create_pr  | done                                         | END (status="done")           |
| fail_task  | done                                         | END (status="failed")         |

Nodes branch ONLY on runners' result dicts (handoff §5) — no subprocess here.
"""

import re
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from . import lock, runners
from .state import TaskState

ATTEMPT_CAP = 3
FIX_CAP = 3


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Paths that must never be staged into the task branch. Starts with the noise
# dirs the dirty-tree guard already ignores (STATUS_NOISE_TOPDIRS: agent
# metadata), plus orch's own state dir and pytest byproducts. Observed
# 2026-09-05: without the noise dirs, .graft/cache.json (58 lines of agent
# metadata) shipped inside PR #6.
_STAGE_EXCLUDES = (
    ":(exclude).orch",
    ":(exclude).graft",
    ":(exclude).opencode",
    ":(exclude).claude",
    ":(exclude).codex",
    ":(exclude)**/__pycache__",
    ":(exclude)**/*.pyc",
    ":(exclude).pytest_cache",
    ":(exclude)**/.pytest_cache",
)


def _stage_excludes() -> list[str]:
    return list(_STAGE_EXCLUDES)


def _slugify(text: str) -> str:
    """수정4 slug rules: first 30 chars -> lower -> non-[a-z0-9] to hyphen ->
    collapse repeats -> strip edges -> cap 30 -> fallback 'task'."""
    text = (text or "").strip().lower()[:30]
    slug = re.sub(r"[^a-z0-9]+", "-", text)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")[:30]
    return slug or "task"


def make_branch_name(origin: str, issue_no: int | None, title: str) -> str:
    """수정4: gh -> orch/gh-<issue>-<slug>, cli -> orch/cli-<YYYYMMDD-HHMMSS>-<slug>."""
    slug = _slugify(title)
    if origin == "github":
        return f"orch/gh-{issue_no}-{slug}"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"orch/cli-{ts}-{slug}"


def make_marker(task_id: str, attempt: int) -> str:
    """v2 §7.5 idempotency marker."""
    return f"orch:{task_id}:attempt={attempt}"


def marker_in_head(repo_path: str, marker: str) -> bool:
    msg = runners.git("log", "-1", "--format=%B", repo_path=repo_path)
    return marker in (msg.get("stdout") or "")


def default_branch_of(repo_path: str) -> str | None:
    """v2 §7.4: query default branch once via gh, fall back to local heuristics."""
    res = runners.gh("repo", "view", "--json", "defaultBranchRef",
                     "-q", ".defaultBranchRef.name", repo_path=repo_path)
    if res["ok"] and res["stdout"].strip():
        return res["stdout"].strip()
    for probe in ("refs/remotes/origin/HEAD",):
        r = runners.git("symbolic-ref", probe, repo_path=repo_path)
        if r["ok"]:
            return r["stdout"].strip().rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        r = runners.git("show-ref", "--verify", f"refs/heads/{candidate}", repo_path=repo_path)
        if r["ok"]:
            return candidate
    return None


def _implement_prompt(plan: str, task: str, marker: str) -> str:
    return (
        "You are implementing a change in the current git repository.\n\n"
        f"TASK:\n{task}\n\n"
        f"APPROVED PLAN:\n{plan}\n\n"
        "REQUIREMENTS:\n"
        "- You MUST make actual code changes (a non-empty git diff is required).\n"
        "- Work only in the working tree; do NOT create, switch, or push git branches.\n"
        "- Do NOT commit; the orchestrator commits.\n"
        "- Do NOT ask questions or wait for input; make reasonable assumptions and act.\n"
        "- Do NOT modify existing tests, docs, or CI workflows "
        "(scripts/tests/*, docs/*, .github/*) — implement the task only.\n"
        "- Do NOT add secrets (API keys, tokens, .env files, private keys).\n"
        f"- Commit marker (informational only): {marker}"
    )


def _fix_prompt(plan: str, test_output: str, marker: str, review_notes: str = "") -> str:
    review_part = (f"\n\nREVIEWER FINDINGS (must also address):\n{review_notes[-3000:]}"
                   if review_notes else "")
    return (
        "The test suite in the current repository is FAILING. Fix the code so the "
        "tests pass. You MUST make actual code changes.\n\n"
        f"PLAN (context):\n{plan}\n\n"
        f"FAILING TEST OUTPUT (tail):\n{test_output[-6000:]}{review_part}\n\n"
        "- Do NOT commit; do NOT touch branches.\n"
        "- Do NOT ask questions or wait for input; make reasonable assumptions and act.\n"
        "- Do NOT modify existing tests, docs, or CI workflows "
        "(scripts/tests/*, docs/*, .github/*) — fix the code only.\n"
        "- Do NOT add secrets.\n"
        f"- Commit marker (informational only): {marker}"
    )


def _review_prompt(plan: str, task: str, diff_stat: str, diff_body: str) -> str:
    return (
        "You are an independent code reviewer. You did NOT write this change.\n"
        "Review ONLY what is shown below. Do NOT make any changes.\n\n"
        f"TASK:\n{task}\n\n"
        f"APPROVED PLAN:\n{plan}\n\n"
        f"DIFF STAT:\n{diff_stat}\n\n"
        f"DIFF (truncated):\n{diff_body[-12000:]}\n\n"
        "Check: (1) does it implement the task and follow the plan; "
        "(2) bugs, edge cases, error handling; "
        "(3) no secrets, no test/doc/CI tampering, no scope creep.\n"
        "End your response with exactly one line: VERDICT: PASS or VERDICT: FAIL."
    )


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

def analyze_signal(status_stdout: str) -> set[str]:
    """Porcelain lines minus benign agent-metadata noise (수정6 fix).

    Single implementation lives in runners.meaningful_status_lines (also
    used by the dirty-tree start guard); this wrapper keeps the graph's
    vocabulary stable.
    """
    return runners.meaningful_status_lines(status_stdout)


def fetch_task(state: TaskState) -> dict:
    """Normalize entry. Lock acquisition happens in cli.py (LockManager) before
    graph.invoke; here we just record that we hold it."""
    return {
        "task_id": state["task_id"],
        "status": "running",
        "attempt": state.get("attempt", 0),
        "fix_attempt": state.get("fix_attempt", 0),
    }


def analyze(state: TaskState) -> dict:
    """Analyze only (forbid_edits). 수정6 integrity guard: worktree must be
    identical before/after modulo agent-metadata noise; violation ->
    analyze_error, NO auto-recovery."""
    repo = state["repo_path"]
    before = runners.git("status", "--porcelain", repo_path=repo)
    if not before["ok"]:
        return {"failure_reason": "analyze_error", "error": before["error"], "status": "failed"}

    res = runners.run_coding_cli(
        "Analyze this repository and produce a concise, actionable implementation "
        "plan for the task below. List files to change and the approach. "
        "Do NOT make any changes. Do NOT ask questions; output only the plan.\n\nTASK:\n" + state["task"],
        forbid_edits=True,
        cwd=repo,
    )
    if not res["ok"] or not res["output"].strip():
        return {
            "failure_reason": "analyze_error",
            "error": res["error"] or "empty plan",
            "status": "failed",
        }

    after = runners.git("status", "--porcelain", repo_path=repo)
    if analyze_signal(after.get("stdout")) != analyze_signal(before.get("stdout")):
        return {
            "failure_reason": "analyze_error",
            "error": "worktree changed during analyze (analyze must not edit)",
            "status": "failed",
        }
    return {"plan": res["output"].strip()}


def create_branch(state: TaskState) -> dict:
    repo = state["repo_path"]
    branch = state.get("branch") or make_branch_name(
        state["origin"], state.get("issue_no"), state["task"]  # slug from the TASK TEXT (수정4)
    )
    exists = runners.git("show-ref", "--verify", f"refs/heads/{branch}", repo_path=repo)
    if not exists["ok"]:
        # Fork explicitly from the base branch — never from the current checkout,
        # which may still sit on a previous task's branch (observed: stacked
        # commits from two tasks landing in one PR).
        base = state.get("default_branch") or default_branch_of(repo) or "main"
        created = runners.git("checkout", "-b", branch, base, repo_path=repo)
        if not created["ok"]:
            return {"failure_reason": "analyze_error", "error": created["error"], "status": "failed"}
    else:
        checked = runners.git("checkout", branch, repo_path=repo)
        if not checked["ok"]:
            return {"failure_reason": "analyze_error", "error": checked["error"], "status": "failed"}
    return {"branch": branch}


def implement(state: TaskState) -> dict:
    """Idempotent re-entry: if this attempt's marker is already in HEAD (v2 §7.5),
    skip re-implementation and go straight to testing."""
    repo = state["repo_path"]
    attempt = state.get("attempt", 0)
    marker = make_marker(state["task_id"], attempt)

    if marker_in_head(repo, marker):
        return {"idempotency_marker": marker, "attempt": attempt, "failure_reason": None}

    res = runners.run_coding_cli(
        _implement_prompt(state["plan"], state["task"], marker), cwd=repo
    )
    if not res["ok"]:
        # 수정8: increment FIRST, then decide. The reason must be set HERE —
        # conditional routers can only choose the next node, never update state.
        new_attempt = attempt + 1
        if new_attempt >= ATTEMPT_CAP:
            return {
                "attempt": new_attempt,
                "failure_reason": "implement_crash",
                "error": res["error"] or res["output"][-2000:],
                "status": "failed",
            }
        return {"attempt": new_attempt, "failure_reason": "implement_crash"}

    # stage + secret scan (v2 §7.3). orch-internal state and caches must never
    # be committed into the task branch.
    add = runners.git("add", "-A", "--", ".", *_stage_excludes(), repo_path=repo)
    if not add["ok"]:
        return {"failure_reason": "implement_crash", "error": add["error"], "status": "failed"}

    diff = runners.git("diff", "--cached", repo_path=repo)
    secrets = runners.check_secrets(diff.get("stdout") or "")
    if secrets:
        runners.git("reset", repo_path=repo)  # unstage; never auto-delete work
        return {"failure_reason": "secret_detected",
                "error": f"secret patterns in staged diff: {', '.join(secrets)}",
                "status": "failed"}

    # 수정5: exit 0 but no changes -> no_changes, attempt NOT consumed
    stat = runners.git("diff", "HEAD", "--stat", repo_path=repo)
    if not (stat.get("stdout") or "").strip():
        return {"failure_reason": "no_changes",
                "error": "coding CLI made no changes (diff vs HEAD empty)",
                "status": "failed"}

    commit = runners.git(
        "commit", "-m",
        f"orch: implement task {state['task_id']}\n\n{marker}\n\n{state['plan'][:400]}",
        repo_path=repo,
    )
    if not commit["ok"]:
        return {"failure_reason": "implement_crash", "error": commit["error"], "status": "failed"}
    # success: clear any stale failure reason (state updates merge per-key)
    return {"idempotency_marker": marker, "attempt": attempt, "failure_reason": None}


def test(state: TaskState) -> dict:
    repo = state["repo_path"]
    res = runners.run_tests(repo)
    if res["passed"] is None:  # v2 §7.6: never guess
        return {"test_result": res, "failure_reason": "no_test_command",
                "error": "no test command detected", "status": "failed"}
    if not res["passed"] and state.get("fix_attempt", 0) >= FIX_CAP:
        # exhaustion decision made here so fail_task receives the reason
        return {"test_result": res, "failure_reason": "test_failed_exhausted",
                "error": "fix cap reached; tests still failing", "status": "failed"}
    # pass or fixable failure: clear stale reasons, continue
    return {"test_result": res, "failure_reason": None}


def fix(state: TaskState) -> dict:
    """fix_attempt increments on ENTRY (수정8). Always returns to test."""
    repo = state["repo_path"]
    fix_attempt = state.get("fix_attempt", 0) + 1
    marker = make_marker(state["task_id"], 1000 + fix_attempt)  # distinct namespace

    if marker_in_head(repo, marker):  # idempotent resume (v2 §7.5)
        return {"fix_attempt": fix_attempt, "idempotency_marker": marker}

    res = runners.run_coding_cli(
        _fix_prompt(state["plan"], (state.get("test_result") or {}).get("output", ""),
                    marker, state.get("review_notes") or ""),
        cwd=repo,
    )
    if not res["ok"]:
        # failed fix run: record and let test decide (re-test still runs; if the
        # repo is broken the same failure persists and eventually exhausts).
        return {"fix_attempt": fix_attempt, "idempotency_marker": marker}

    add = runners.git("add", "-A", "--", ".", *_stage_excludes(), repo_path=repo)
    diff = runners.git("diff", "--cached", repo_path=repo)
    secrets = runners.check_secrets(diff.get("stdout") or "")
    if not add["ok"] or secrets:
        if add["ok"]:
            runners.git("reset", repo_path=repo)
        if secrets:  # v2 §7.3: abort via fail_task (after_fix edge)
            return {"fix_attempt": fix_attempt,
                    "failure_reason": "secret_detected",
                    "error": f"secret patterns in staged diff: {', '.join(secrets)}",
                    "status": "failed"}
        return {"fix_attempt": fix_attempt,
                "error": f"fix staging failed: {add.get('error')}"}

    stat = runners.git("diff", "HEAD", "--stat", repo_path=repo)
    if (stat.get("stdout") or "").strip():
        runners.git("commit", "-m",
                    f"orch: fix task {state['task_id']} (fix {fix_attempt})\n\n{marker}",
                    repo_path=repo)
    return {"fix_attempt": fix_attempt, "idempotency_marker": marker, "failure_reason": None}


def review(state: TaskState) -> dict:
    """Independent review before PR (P3). Read-only; strict verdict parsing:
    missing/unparseable VERDICT counts as rejection (never PR unreviewed)."""
    repo = state["repo_path"]
    base = state.get("default_branch") or default_branch_of(repo) or "main"
    stat = runners.git("diff", f"{base}...HEAD", "--stat", repo_path=repo)
    body = runners.git("diff", f"{base}...HEAD", repo_path=repo)
    res = runners.run_coding_cli(
        _review_prompt(state["plan"], state["task"],
                       (stat.get("stdout") or "")[:2000],
                       body.get("stdout") or ""),
        forbid_edits=True,
        cwd=repo,
        role="review",
    )
    if not res["ok"]:
        return {"review_passed": False,
                "review_notes": f"reviewer CLI failed: {res['error'] or 'unknown'}"}
    m = re.search(r"^VERDICT:\s*(PASS|FAIL)\s*$", res["output"] or "", re.M | re.I)
    if m and m.group(1).upper() == "PASS":
        return {"review_passed": True, "review_notes": res["output"].strip()[-2000:]}
    notes = res["output"].strip()[-4000:] or "no verdict line"
    if state.get("fix_attempt", 0) >= FIX_CAP:
        return {"review_passed": False, "review_notes": notes,
                "failure_reason": "test_failed_exhausted",
                "error": "review rejected and fix cap reached", "status": "failed"}
    return {"review_passed": False, "review_notes": notes}


def create_pr(state: TaskState) -> dict:
    """수정1 order: ref guard -> push -> existing-PR check -> create -> record."""
    repo = state["repo_path"]
    branch = state["branch"]
    base = state.get("default_branch") or default_branch_of(repo) or "main"

    push = runners.git("push", "-u", "origin", branch, repo_path=repo)
    if not push["ok"]:
        # the 8-value failure taxonomy has no PR-stage reason; implement_crash
        # is the closest — the concrete cause lives in `error`.
        return {"failure_reason": "implement_crash", "error": push["error"], "status": "failed"}

    existing = runners.gh("pr", "list", "--head", branch, "--json", "url",
                          "-q", ".[0].url", repo_path=repo)  # 수정2 duplicate guard
    if existing["ok"] and existing["stdout"].strip():
        pr_url = existing["stdout"].strip()
    else:
        title = f"orch: {state['task_id']}"
        body = f"Automated by orch.\n\nTask:\n{state['task']}\n\nPlan:\n{state['plan']}"
        created = runners.gh("pr", "create", "--base", base, "--head", branch,
                             "--title", title, "--body", body, repo_path=repo)
        if not created["ok"]:
            return {"failure_reason": "implement_crash", "error": created["error"], "status": "failed"}
        pr_url = created["stdout"].strip()

    # GitHub origin: comment the PR link on the issue (v2 §6.2)
    if state["origin"] == "github" and state.get("issue_no") and state.get("pr_url") != pr_url:
        runners.gh("issue", "comment", str(state["issue_no"]),
                   "--body", f"orch created a PR: {pr_url}", repo_path=repo)

    return {"pr_url": pr_url, "status": "done", "failure_reason": None}


def fail_task(state: TaskState) -> dict:
    """수정10: github -> failure comment; cli -> stdout; keep checkpoint, keep
    branch. Lock release handled by LockManager in cli.py."""
    reason = state.get("failure_reason") or "unknown"
    detail = state.get("error") or ""
    msg = f"orch task failed: {reason}\n{detail}"

    if state["origin"] == "github" and state.get("issue_no"):
        runners.gh("issue", "comment", str(state["issue_no"]),
                   "--body", msg, repo_path=state["repo_path"])
    print(f"[orch] FAIL task={state['task_id']} reason={reason}\n{detail}")
    return {"status": "failed", "failure_reason": reason, "error": detail}


# ---------------------------------------------------------------------------
# conditional edges
# ---------------------------------------------------------------------------

def after_fetch(state: TaskState) -> str:
    return "fail_task" if state.get("failure_reason") == "lock_unavailable" else "analyze"


def after_analyze(state: TaskState) -> str:
    return "fail_task" if state.get("failure_reason") == "analyze_error" else "create_branch"


def after_implement(state: TaskState) -> str:
    reason = state.get("failure_reason")
    if reason in ("secret_detected", "no_changes"):
        return "fail_task"
    if reason == "implement_crash":
        return "fail_task" if state.get("attempt", 0) >= ATTEMPT_CAP else "implement"
    return "test"


def after_test(state: TaskState) -> str:
    if state.get("failure_reason") in ("no_test_command", "secret_detected"):
        return "fail_task"
    passed = (state.get("test_result") or {}).get("passed")
    if passed:
        return "review"
    if state.get("fix_attempt", 0) < FIX_CAP:
        return "fix"
    return "fail_task"


def after_review(state: TaskState) -> str:
    """PASS -> PR. Rejection -> fix (fix_attempt increments on fix entry, so
    the cap still bounds the loop). Rejection at cap arrives with
    failure_reason already set by the review node -> fail_task."""
    if state.get("failure_reason"):
        return "fail_task"
    return "create_pr" if state.get("review_passed") else "fix"


def after_fix(state: TaskState) -> str:
    """v2 change #1: fix returns to test — EXCEPT a secret abort (v2 §7.3),
    which must go straight to fail_task."""
    if state.get("failure_reason") == "secret_detected":
        return "fail_task"
    return "test"


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    g = StateGraph(TaskState)
    g.add_node("fetch_task", fetch_task)
    g.add_node("analyze", analyze)
    g.add_node("create_branch", create_branch)
    g.add_node("implement", implement)
    g.add_node("test", test)
    g.add_node("fix", fix)
    g.add_node("review", review)
    g.add_node("create_pr", create_pr)
    g.add_node("fail_task", fail_task)

    g.add_edge(START, "fetch_task")
    g.add_conditional_edges("fetch_task", after_fetch, {"analyze": "analyze", "fail_task": "fail_task"})
    g.add_conditional_edges("analyze", after_analyze,
                            {"create_branch": "create_branch", "fail_task": "fail_task"})
    g.add_edge("create_branch", "implement")
    g.add_conditional_edges("implement", after_implement,
                            {"test": "test", "implement": "implement", "fail_task": "fail_task"})
    g.add_conditional_edges("test", after_test,
                            {"review": "review", "fix": "fix", "fail_task": "fail_task"})
    # v2 change #1: ALWAYS re-test after fix — except the §7.3 secret abort
    g.add_conditional_edges("fix", after_fix, {"test": "test", "fail_task": "fail_task"})
    g.add_conditional_edges("review", after_review,
                            {"create_pr": "create_pr", "fix": "fix", "fail_task": "fail_task"})
    g.add_edge("create_pr", END)
    g.add_edge("fail_task", END)
    return g.compile(checkpointer=checkpointer)


def new_task_id(origin: str) -> str:
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"gh-{now}" if origin == "github" else f"cli-{now}"
