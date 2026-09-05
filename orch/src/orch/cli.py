"""orch CLI: run / watch / resume / unlock.

- run: one-shot task from the terminal (CLI origin).
- watch: poll GitHub issues labeled `orch` and process them FIFO (poller.py).
- resume: continue a checkpointed task (thread_id == task_id, 수정9).
- unlock --force: human override for a stuck repo lock (수정3).

Locking: every graph execution takes the repo lock via LockManager
(finally + atexit + SIGINT/SIGTERM handlers, 수정3). CLI `run` that cannot get
the lock fails immediately with lock_unavailable (v2 §7.1).

Secrets never touch the graph: prompts are built from the task text only.
"""

import argparse
import hashlib
import os
import sys

from . import graph as graph_mod
from . import lock, runners
from .state import TaskState

DEFAULT_REPO_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),  # Limagination/
    os.getcwd(),
]


def _default_repo() -> str:
    """--repo default: v1 target is the sibling soul-commander checkout."""
    limagination = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sibling = os.path.join(limagination, "soul-commander")
    if os.path.isdir(os.path.join(sibling, ".git")):
        return sibling
    return os.getcwd()


def _new_task_id() -> str:
    from datetime import datetime
    return f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _resolve_repo(path: str | None) -> str:
    repo = os.path.abspath(path or _default_repo())
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"[orch] error: {repo} is not a git repository", file=sys.stderr)
        raise SystemExit(2)
    return repo


def _initial_state(task_id: str, origin: str, repo: str, task: str, issue_no: int | None = None) -> TaskState:
    return TaskState(
        task_id=task_id,
        task=task,
        origin=origin,
        issue_no=issue_no,
        repo_path=repo,
        default_branch=None,
        branch=None,
        plan="",
        attempt=0,
        fix_attempt=0,
        test_result={},
        review_passed=None,
        review_notes="",
        pr_url=None,        status="running",
        error=None,
        failure_reason=None,
        idempotency_marker=None,
    )


def _orch_home() -> str:
    """orch's own state dir: <orch project root>/.orch (design v2 §3), where the
    project root is found by walking up to pyproject.toml from this file."""
    if os.environ.get("ORCH_HOME"):
        return os.environ["ORCH_HOME"]
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "pyproject.toml")):
            return os.path.join(d, ".orch")
        d = os.path.dirname(d)
    return os.path.join(os.getcwd(), ".orch")


def db_slug_for_repo(repo: str) -> str:
    """Stable per-repo slug: <basename>-<sha1(path)[:8]>. Same repo (CLI or
    server) always maps to the same checkpoints DB file."""
    abspath = os.path.abspath(repo)
    digest = hashlib.sha1(abspath.encode("utf-8")).hexdigest()[:8]
    base = os.path.basename(abspath.rstrip(os.sep)) or "repo"
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in base).strip("-") or "repo"
    return f"{safe[:40]}-{digest}"


def db_path_for_repo(repo: str) -> str:
    """Per-repo checkpoints DB (dashboard spec §2). Legacy global
    checkpoints.db is only a read fallback for pre-separation tasks."""
    return os.path.join(_orch_home(), f"checkpoints-{db_slug_for_repo(repo)}.db")


def _legacy_db_path() -> str:
    return os.path.join(_orch_home(), "checkpoints.db")


def _make_checkpointer(repo: str | None = None):
    """Sqlite checkpointer if available; None degrades to non-resumable runs.

    repo given -> ALWAYS the per-repo DB (created on first write). The legacy
    global DB is never written anymore; old tasks are found through
    get_checkpoint_tuple(), which falls back to it for reads.
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3

        state_dir = _orch_home()
        os.makedirs(state_dir, exist_ok=True)
        path = _legacy_db_path() if repo is None else db_path_for_repo(repo)
        conn = sqlite3.connect(path, check_same_thread=False)
        return SqliteSaver(conn)
    except Exception as e:  # pragma: no cover
        print(f"[orch] warning: checkpointer unavailable ({e}); resume disabled", file=sys.stderr)
        return None


def get_checkpoint_tuple(repo: str, task_id: str):
    """Latest checkpoint for task_id: per-repo DB first, legacy global DB as
    read fallback (pre-separation tasks stay resumable). Returns None or raises."""
    cp = _make_checkpointer(repo)
    saved = cp.get_tuple({"configurable": {"thread_id": task_id}}) if cp else None
    if saved is None:
        legacy = _legacy_db_path()
        if os.path.exists(legacy) and os.path.abspath(legacy) != os.path.abspath(db_path_for_repo(repo)):
            lcp = _make_checkpointer(None)
            if lcp is not None:
                saved = lcp.get_tuple({"configurable": {"thread_id": task_id}})
    return saved


def _dry_run(state: TaskState) -> int:
    """--dry-run: analyze only, print plan, change nothing. Exit 0 on success.

    Delegates to the real graph.analyze node so the 수정6 guard lives in
    exactly one place (no duplicated status comparison here).
    """
    res = graph_mod.analyze(state)
    if res.get("failure_reason"):
        if "worktree changed" in (res.get("error") or ""):
            print("[orch] DRY-RUN VIOLATION: worktree changed during analyze; aborting")
        else:
            print(f"[orch] dry-run failed: {res.get('error') or res['failure_reason']}")
        return 1
    print("=== PLAN (dry-run) ===")
    print(res["plan"].strip())
    print("=== END PLAN ===")
    return 0


def _run_graph(state: TaskState) -> TaskState:
    checkpointer = _make_checkpointer(state.get("repo_path"))
    app = graph_mod.build_graph(checkpointer=checkpointer)
    thread_config = {"configurable": {"thread_id": state["task_id"]}}  # 수정9
    final = app.invoke(state, config=thread_config)
    return final


def execute_run(repo: str, task_text: str, task_id: str | None = None) -> dict:
    """Programmatic one-shot run (CLI and server share this; no prints).

    Raises lock.LockUnavailable when the repo is busy, and
    runners.DirtyTreeError when the worktree has uncommitted user changes
    (they would be swept into the task commit via `git add -A`).
    Returns the final state as a plain dict.
    """
    tid = task_id or _new_task_id()
    runners.assert_clean_tree(repo)
    with lock.LockManager(repo, tid):
        state = _initial_state(tid, "cli", repo, task_text)
        return dict(_run_graph(state))


def execute_resume(repo: str, task_id: str, reset_attempts: bool = False) -> dict:
    """Programmatic resume. Returns {"ok", "final"|"error"}; raises
    lock.LockUnavailable when the repo is busy."""
    checkpointer = _make_checkpointer(repo)
    if checkpointer is None:
        return {"ok": False, "code": 2, "error": "checkpointer unavailable; resume is not possible"}

    saved = None
    try:
        saved = get_checkpoint_tuple(repo, task_id)
    except Exception as e:
        return {"ok": False, "code": 2, "error": f"cannot read checkpoint for {task_id}: {e}"}
    if saved is None:
        return {"ok": False, "code": 2, "error": f"no checkpoint found for task {task_id}"}
    saved_values = saved.checkpoint.get("channel_values", {}) if saved.checkpoint else {}
    # keep only schema channels — the checkpoint blob also holds pregel internals
    saved_values = {k: v for k, v in saved_values.items() if k in TaskState.__annotations__}

    if reset_attempts:  # v2 §7.7
        saved_values["attempt"] = 0
        saved_values["fix_attempt"] = 0
        print("[orch] --reset-attempts: counters reset to 0")

    if saved_values.get("failure_reason") and not reset_attempts:
        # already at a terminal failed state: refuse without explicit reset (v2 §7.7)
        return {"ok": False, "code": 1,
                "error": f"task {task_id} already failed "
                         f"({saved_values.get('failure_reason')}); use --reset-attempts to retry"}

    with lock.LockManager(repo, task_id):
        final = dict(_run_graph(dict(saved_values)))
    return {"ok": True, "code": 0, "final": final, "reset": reset_attempts}


def cmd_run(args) -> int:
    repo = _resolve_repo(args.repo)
    task_id = _new_task_id()

    try:
        if args.dry_run:
            with lock.LockManager(repo, task_id, log=lambda m: print(f"[orch] {m}")):
                state = _initial_state(task_id, "cli", repo, args.task)
                return _dry_run(state)
        final = execute_run(repo, args.task, task_id)
        status = final.get("status")
        print(f"[orch] task {task_id}: {status}"
              + (f" pr={final.get('pr_url')}" if final.get("pr_url") else "")
              + (f" reason={final.get('failure_reason')}" if final.get("failure_reason") else ""))
        return 0 if status == "done" else 1
    except runners.NotARepoError as e:
        print(f"[orch] REFUSED task={task_id} reason=not_a_repo\n{e}")
        return 2
    except runners.DirtyTreeError as e:
        print(f"[orch] REFUSED task={task_id} reason=dirty_tree\n{e}")
        return 2
    except lock.LockUnavailable as e:
        print(f"[orch] FAIL task={task_id} reason=lock_unavailable\n{e}")
        return 1


def cmd_watch(args) -> int:
    from .poller import watch_loop
    repo = _resolve_repo(args.repo)
    return watch_loop(repo, interval_s=args.interval)


def cmd_resume(args) -> int:
    repo = _resolve_repo(args.repo)
    task_id = args.task_id

    try:
        res = execute_resume(repo, task_id, reset_attempts=args.reset_attempts)
    except lock.LockUnavailable as e:
        print(f"[orch] FAIL task={task_id} reason=lock_unavailable\n{e}")
        return 1
    if not res["ok"]:
        print(f"[orch] error: {res['error']}" if res["code"] == 2 else f"[orch] {res['error']}",
              file=sys.stderr if res["code"] == 2 else None)
        return res["code"]
    final = res["final"]
    status = final.get("status")
    print(f"[orch] task {task_id}: {status}"
          + (f" pr={final.get('pr_url')}" if final.get("pr_url") else "")
          + (f" reason={final.get('failure_reason')}" if final.get("failure_reason") else ""))
    return 0 if status == "done" else 1


def cmd_unlock(args) -> int:
    repo = _resolve_repo(args.repo)
    removed = lock.unlock_force(repo, log=lambda m: print(f"[orch] {m}"))
    return 0 if removed else 1


def cmd_serve(args) -> int:
    from .server import install_service, uninstall_service
    if args.install:
        print(f"[orch] service installed: {install_service(args.port)}")
        return 0
    if args.uninstall:
        print("[orch] service removed" if uninstall_service() else "[orch] no service found")
        return 0
    from .server import serve
    return serve(args.port, args.repos)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orch", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="one-shot task: analyze -> implement -> test -> PR")
    run_p.add_argument("task", help="task description (quoted string)")
    run_p.add_argument("--repo", default=None, help="target repo (default: sibling soul-commander or cwd)")
    run_p.add_argument("--dry-run", action="store_true", help="analyze only; print plan; change nothing")
    run_p.set_defaults(func=cmd_run)

    watch_p = sub.add_parser("watch", help="poll GitHub issues labeled 'orch' and process FIFO")
    watch_p.add_argument("--repo", default=None)
    watch_p.add_argument("--interval", type=int, default=60, help="poll interval seconds (default 60)")
    watch_p.set_defaults(func=cmd_watch)

    resume_p = sub.add_parser("resume", help="resume a checkpointed task (thread_id == task_id)")
    resume_p.add_argument("task_id")
    resume_p.add_argument("--repo", default=None)
    resume_p.add_argument("--reset-attempts", action="store_true",
                          help="reset attempt/fix_attempt counters before resuming (v2 §7.7)")
    resume_p.set_defaults(func=cmd_resume)

    unlock_p = sub.add_parser("unlock", help="force-remove the repo lock (human override)")
    unlock_p.add_argument("--repo", default=None)
    unlock_p.set_defaults(func=cmd_unlock)

    serve_p = sub.add_parser("serve", help="dashboard backend (localhost web UI)")
    serve_p.add_argument("--port", type=int, default=8471)
    serve_p.add_argument("--repos", default="",
                         help="alias=/path,... merged into ~/.orch-repos.json")
    serve_p.add_argument("--install", action="store_true",
                         help="register login-start service (macOS launchd)")
    serve_p.add_argument("--uninstall", action="store_true",
                         help="remove login-start service")
    serve_p.set_defaults(func=cmd_serve)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
