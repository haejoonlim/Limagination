"""Dashboard backend tests (stdlib HTTP, no agent calls).

Covers spec §6.4: routing, checkpoint reading, per-repo DB separation.
Real graph runs are covered by the existing e2e flow, not here — the
/rerun worker is stubbed via monkeypatch.
"""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from typing import TypedDict

import pytest

from orch import cli, lock, server


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mk_git_repo(path) -> str:
    import subprocess
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    return str(path)


def _http(base, method, path, body=None):
    data = json.dumps(body or {}).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCH_HOME", str(tmp_path / "oh"))
    monkeypatch.setenv("ORCH_REPOS", str(tmp_path / "repos.json"))
    repo = _mk_git_repo(tmp_path / "r")
    server.save_registry({"t": repo})
    return repo


@pytest.fixture()
def srv(env):
    reg = server.load_registry()
    state = server.ServerState(reg)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.state = state
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{httpd.server_port}", state
    httpd.shutdown()
    httpd.server_close()


# ---------------------------------------------------------------------------
# registry + slug
# ---------------------------------------------------------------------------

def test_registry_roundtrip(env):
    assert server.load_registry() == {"t": env}
    server.save_registry({"a": env})
    assert server.load_registry() == {"a": env}


def test_parse_repos_arg(tmp_path):
    r = tmp_path / "x"
    _mk_git_repo(r)
    assert server.parse_repos_arg(f"a={r}") == {"a": str(r)}
    assert server.parse_repos_arg(str(r)) == {"x": str(r)}
    assert server.parse_repos_arg("a=/nonexistent") == {}
    assert server.parse_repos_arg("") == {}


def test_db_slug_stable_and_distinct(tmp_path):
    a = str(tmp_path / "same")
    assert cli.db_slug_for_repo(a) == cli.db_slug_for_repo(a + "/")
    assert cli.db_slug_for_repo(str(tmp_path / "one")) != cli.db_slug_for_repo(str(tmp_path / "two"))


# ---------------------------------------------------------------------------
# checkpoint listing (real SqliteSaver, trivial graph — no agents)
# ---------------------------------------------------------------------------

class _S(TypedDict):
    task_id: str
    status: str


def _write_checkpoint(repo: str, task_id: str, status: str) -> None:
    from langgraph.graph import END, START, StateGraph

    def n(s):
        return {"task_id": task_id, "status": status}

    g = StateGraph(_S)
    g.add_node("n", n)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    app = g.compile(checkpointer=cli._make_checkpointer(repo))
    app.invoke({"task_id": task_id, "status": "running"},
               {"configurable": {"thread_id": task_id}})


def test_list_tasks_empty_without_db(env):
    assert server.list_tasks(env) == []


def test_list_tasks_reads_latest_and_isolates_repos(env, tmp_path):
    other = _mk_git_repo(tmp_path / "other")
    _write_checkpoint(env, "t-1", "done")
    _write_checkpoint(env, "t-2", "failed")
    got = {t["task_id"]: t["status"] for t in server.list_tasks(env)}
    assert got == {"t-1": "done", "t-2": "failed"}
    assert server.list_tasks(other) == []
    assert cli.db_path_for_repo(env) != cli.db_path_for_repo(other)


def test_new_writes_go_to_per_repo_db_never_legacy(env, tmp_path):
    """Regression: while the legacy global DB exists, new runs must still
    create/write the per-repo DB (fallback is read-only)."""
    legacy = tmp_path / "oh" / "checkpoints.db"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"placeholder")
    _write_checkpoint(env, "t-new", "done")
    assert cli.db_path_for_repo(env) != str(legacy)
    assert legacy.read_bytes() == b"placeholder"
    got = {t["task_id"]: t["status"] for t in server.list_tasks(env)}
    assert got == {"t-new": "done"}


def test_legacy_task_found_via_fallback(env, tmp_path):
    """Pre-separation tasks in the global DB stay resumable."""
    from langgraph.graph import END, START, StateGraph

    legacy = tmp_path / "oh" / "checkpoints.db"

    def n(s):
        return {"task_id": "t-old", "status": "failed"}

    g = StateGraph(_S)
    g.add_node("n", n)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    app = g.compile(checkpointer=cli._make_checkpointer(None))
    app.invoke({"task_id": "t-old", "status": "running"},
               {"configurable": {"thread_id": "t-old"}})
    assert legacy.exists()
    saved = cli.get_checkpoint_tuple(env, "t-old")
    assert saved is not None
    # ...but the per-repo listing stays isolated (legacy not listed)
    assert server.list_tasks(env) == []


# ---------------------------------------------------------------------------
# HTTP routes (workers stubbed)
# ---------------------------------------------------------------------------

def test_dashboard_served(srv):
    base, _state = srv
    with urllib.request.urlopen(base + "/", timeout=10) as r:
        assert r.status == 200
        assert "orch dashboard" in r.read().decode()


def test_repos_and_unknown_alias(srv):
    base, _state = srv
    code, body = _http(base, "GET", "/api/repos")
    assert code == 200 and body["repos"][0]["alias"] == "t"
    assert body["repos"][0]["locked"] is False
    code, _ = _http(base, "GET", "/api/tasks?repo=nope")
    assert code == 400


def test_run_route_starts_worker(srv, monkeypatch):
    import orch.server as srvmod

    base, state = srv
    calls = []

    def fake_run(repo_path, task_text, task_id):
        calls.append((repo_path, task_text, task_id))
        return {"status": "done", "pr_url": "http://x/1", "failure_reason": None}

    monkeypatch.setattr(cli, "execute_run", fake_run)
    code, body = _http(base, "POST", "/api/run", {"repo": "t", "task": "hello"})
    assert code == 202 and body["task_id"].startswith("cli-")
    deadline = __import__("time").monotonic() + 10
    while body["task_id"] in state.running and __import__("time").monotonic() < deadline:
        __import__("time").sleep(0.05)
    assert calls and calls[0][1] == "hello"
    assert state.results[body["task_id"]]["status"] == "done"

    code, _ = _http(base, "POST", "/api/run", {"repo": "t", "task": ""})
    assert code == 400
    code, _ = _http(base, "POST", "/api/run", {"repo": "nope", "task": "x"})
    assert code == 400


def test_run_route_409_when_locked(srv, env):
    base, _state = srv
    lock.acquire(env, "holder")
    try:
        code, body = _http(base, "POST", "/api/run", {"repo": "t", "task": "x"})
        assert code == 409 and body["error"] == "lock_unavailable"
    finally:
        lock.release(env)


def test_run_route_409_when_dirty(srv, env):
    base, _state = srv
    with open(f"{env}/uncommitted.txt", "w") as f:
        f.write("user work in progress")
    code, body = _http(base, "POST", "/api/run", {"repo": "t", "task": "x"})
    assert code == 409 and body["error"] == "dirty_tree"


def test_resume_route(srv, monkeypatch):
    base, state = srv

    def fake_resume(repo_path, task_id, reset_attempts=False):
        return {"ok": True, "code": 0,
                "final": {"status": "done", "pr_url": None, "failure_reason": None},
                "reset": reset_attempts}

    monkeypatch.setattr(cli, "execute_resume", fake_resume)
    code, body = _http(base, "POST", "/api/resume",
                       {"repo": "t", "task_id": "cli-1", "reset_attempts": True})
    assert code == 202
    code, _ = _http(base, "POST", "/api/resume", {"repo": "t", "task_id": ""})
    assert code == 400


def test_watch_start_stop(srv, monkeypatch):
    import orch.server as srvmod

    base, state = srv
    gate = threading.Event()

    def fake_watch(*a, **k):
        gate.wait(timeout=10)
        return 0

    monkeypatch.setattr(srvmod, "watch_loop", fake_watch)
    code, body = _http(base, "POST", "/api/watch", {"repo": "t", "interval": 60})
    assert code == 202 and body["watching"] is True
    code, body = _http(base, "POST", "/api/watch", {"repo": "t"})
    assert code == 409  # already watching while the first loop holds the slot
    code, body = _http(base, "POST", "/api/watch", {"repo": "t", "stop": True})
    assert code == 200 and body["watching"] is False
    gate.set()
