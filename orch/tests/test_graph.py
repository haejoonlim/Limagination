"""Graph topology tests with runners fully stubbed via monkeypatch (no
subprocess coding-CLI calls; real git runs only inside the tmp fixture repo).

Covers the v2.1 edge table: fix->test regression (v2 change #1), attempt/fix
off-by-one rules (수정8), no_changes branch (수정5), secret blocking (v2 §7.3),
PR duplicate guard (수정2), push before pr create (수정1).
"""

import subprocess
from types import SimpleNamespace

import pytest

import orch.graph as g
from orch import runners
from orch.graph import (
    after_analyze,
    after_implement,
    after_test,
    analyze_signal,
    build_graph,
    make_marker,
)
from orch.state import TaskState


# ---------------------------------------------------------------------------
# conditional-edge unit tests (pure, dict-like stubs)
# ---------------------------------------------------------------------------

class _S(dict):
    """dict with attribute access — graph edge functions use .get() and [] only."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def _s(**kw):
    base = dict(failure_reason=None, attempt=0, fix_attempt=0,
                test_result={"passed": True}, task_id="cli-1")
    base.update(kw)
    return _S(base)


def test_after_analyze_ok():
    assert after_analyze(_s()) == "create_branch"


def test_after_analyze_error():
    assert after_analyze(_s(failure_reason="analyze_error")) == "fail_task"


def test_after_implement_routes_no_changes():
    assert after_implement(_s(failure_reason="no_changes")) == "fail_task"


def test_after_implement_routes_secret():
    assert after_implement(_s(failure_reason="secret_detected")) == "fail_task"


def test_after_implement_crash_retries_below_cap():
    assert after_implement(_s(failure_reason="implement_crash", attempt=1)) == "implement"


def test_after_implement_crash_fails_at_cap():
    assert after_implement(_s(failure_reason="implement_crash", attempt=3)) == "fail_task"


def test_after_test_pass():
    assert after_test(_s(test_result={"passed": True})) == "review"


def test_after_test_fail_goes_to_fix_then_exhausts():
    assert after_test(_s(test_result={"passed": False}, fix_attempt=0)) == "fix"
    assert after_test(_s(test_result={"passed": False}, fix_attempt=2)) == "fix"
    assert after_test(_s(test_result={"passed": False}, fix_attempt=3)) == "fail_task"


def test_after_test_no_test_command():
    assert after_test(_s(failure_reason="no_test_command")) == "fail_task"


# ---------------------------------------------------------------------------
# shared fixtures / helpers
# ---------------------------------------------------------------------------

def _real_git(repo_path, *args):
    proc = subprocess.run(["git", *args], cwd=repo_path, capture_output=True, text=True)
    return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr,
            "error": None if proc.returncode == 0 else proc.stderr}


@pytest.fixture()
def git_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    return str(tmp_path)


@pytest.fixture()
def stubs(monkeypatch, git_repo):
    """Stub runners used by graph nodes; real git executes inside the fixture."""
    calls = {"cli": [], "gh": [], "tests": 0}
    box = SimpleNamespace(calls=calls, repo=git_repo)

    def fake_cli(prompt, *, timeout_s=1200, forbid_edits=False, cwd=None, **kw):
        calls["cli"].append({"forbid": forbid_edits, "prompt_head": prompt[:50]})
        if forbid_edits:
            if "independent code reviewer" in prompt:
                return {"ok": True, "output": "looks good\nVERDICT: PASS", "error": None}
            return {"ok": True, "output": "PLAN: add docstring", "error": None}
        with open(f"{cwd}/calc.py", "a") as f:  # cwd is the fixture repo (absolute)
            f.write("# orch was here\n")
        return {"ok": True, "output": "done", "error": None}

    def fake_tests(repo_path):
        calls["tests"] += 1
        return {"passed": True, "output": "1 passed", "command": "pytest"}

    def fake_git(*args, repo_path):
        if args[0] == "push":  # no remote in fixture; pretend it succeeded
            return {"ok": True, "stdout": "", "stderr": "", "error": None}
        return _real_git(repo_path, *args)

    def fake_gh(*args, repo_path=None):
        calls["gh"].append(args)
        joined = " ".join(args)
        if joined.startswith("pr list"):
            return {"ok": True, "stdout": "", "stderr": "", "error": None}
        if joined.startswith("pr create"):
            return {"ok": True, "stdout": "https://example.test/pr/1", "stderr": "", "error": None}
        if joined.startswith("repo view"):
            return {"ok": True, "stdout": "main", "stderr": "", "error": None}
        return {"ok": True, "stdout": "", "stderr": "", "error": None}

    monkeypatch.setattr(runners, "run_coding_cli", fake_cli)
    monkeypatch.setattr(runners, "run_tests", fake_tests)
    monkeypatch.setattr(runners, "git", fake_git)
    monkeypatch.setattr(runners, "gh", fake_gh)
    monkeypatch.setattr(g, "runners", runners)
    return box


def _base_state(repo, task_id="cli-test"):
    return TaskState(
        task_id=task_id, task="add a docstring to calc.add", origin="cli", issue_no=None,
        repo_path=repo, default_branch=None, branch=None, plan="",
        attempt=0, fix_attempt=0, test_result={}, pr_url=None, status="running",
        error=None, failure_reason=None, idempotency_marker=None,
    )


def _invoke(state):
    app = build_graph()
    return app.invoke(state, config={"configurable": {"thread_id": state["task_id"]}})


# ---------------------------------------------------------------------------
# full-graph tests
# ---------------------------------------------------------------------------

def test_full_graph_happy_path(stubs):
    state = _base_state(stubs.repo)
    final = _invoke(state)

    assert final["status"] == "done"
    assert final["pr_url"] == "https://example.test/pr/1"
    assert final["branch"].startswith("orch/cli-")
    # one analyze + one implement + one review (no retries)
    assert [c["forbid"] for c in stubs.calls["cli"]] == [True, False, True]
    # tests ran once, passed, went to review then PR
    assert stubs.calls["tests"] == 1
    # commit carries the idempotency marker (v2 §7.5)
    log = _real_git(stubs.repo, "log", "-1", "--format=%B")["stdout"]
    assert make_marker("cli-test", 0) in log
    # push before pr create: gh saw only PR calls (수정1 — push is real git stub)
    assert any(" ".join(a).startswith("pr create") for a in stubs.calls["gh"])


def test_agent_metadata_never_committed(stubs):
    """Regression (2026-09-05): .graft/cache.json (58 lines of agent metadata)
    shipped inside PR #6. Noise dirs (.graft/.opencode/.claude/.codex) must
    never reach the task branch — the same set the dirty-tree guard ignores.
    """
    import os
    os.makedirs(os.path.join(stubs.repo, ".graft"))
    open(os.path.join(stubs.repo, ".graft", "cache.json"), "w").write("{\"a\": 1}")
    os.makedirs(os.path.join(stubs.repo, "__pycache__"))
    open(os.path.join(stubs.repo, "__pycache__", "x.pyc"), "w").write("b")

    final = _invoke(_base_state(stubs.repo, task_id="cli-metadata"))
    assert final["status"] == "done"

    # the agent's edit is committed, metadata dirs are NOT
    tracked = _real_git(stubs.repo, "ls-files")["stdout"]
    assert "calc.py" in tracked
    assert ".graft" not in tracked
    assert "__pycache__" not in tracked
    # recursive check: nothing under HEAD carries metadata paths
    head_files = _real_git(stubs.repo, "ls-tree", "-r", "--name-only", "HEAD")["stdout"]
    assert all(
        ".graft" not in f and ".opencode" not in f and ".claude" not in f
        and ".codex" not in f and "__pycache__" not in f and ".pytest_cache" not in f
        for f in head_files.splitlines()
    )


def test_fix_loop_returns_to_test(stubs, monkeypatch):
    """v2 change #1 regression: failing test -> fix -> test again -> pass."""
    state = _base_state(stubs.repo, task_id="cli-fixloop")
    runs = {"n": 0}

    def flaky_tests(repo_path):
        runs["n"] += 1
        return ({"passed": False, "output": "1 failed", "command": "pytest"}
                if runs["n"] == 1
                else {"passed": True, "output": "ok", "command": "pytest"})

    monkeypatch.setattr(runners, "run_tests", flaky_tests)
    final = _invoke(state)

    assert final["status"] == "done"
    assert runs["n"] == 2  # re-tested after fix — THE regression check
    assert final["fix_attempt"] == 1
    assert final["pr_url"]


def test_fix_exhaustion_fails_task(stubs, monkeypatch):
    state = _base_state(stubs.repo, task_id="cli-exhaust")
    monkeypatch.setattr(runners, "run_tests",
                        lambda repo: {"passed": False, "output": "failing", "command": "pytest"})
    final = _invoke(state)

    assert final["status"] == "failed"
    assert final["failure_reason"] == "test_failed_exhausted"
    assert final["fix_attempt"] == 3  # exactly the cap, then stop (수정8)
    assert final["attempt"] == 0


def test_implement_no_changes_fails_without_consuming_attempt(stubs, monkeypatch):
    """수정5: CLI exit 0 but empty diff -> no_changes; attempt NOT consumed."""
    state = _base_state(stubs.repo, task_id="cli-nodiff")

    def no_edit_cli(prompt, *, timeout_s=1200, forbid_edits=False, cwd=None):
        if forbid_edits:
            return {"ok": True, "output": "PLAN", "error": None}
        return {"ok": True, "output": "no changes needed", "error": None}

    monkeypatch.setattr(runners, "run_coding_cli", no_edit_cli)
    final = _invoke(state)

    assert final["status"] == "failed"
    assert final["failure_reason"] == "no_changes"
    assert final["attempt"] == 0


def test_implement_crash_retries_then_fails(stubs, monkeypatch):
    """수정8: attempt increments BEFORE decision; exactly 3 runs total."""
    state = _base_state(stubs.repo, task_id="cli-crash")
    attempts = {"n": 0}

    def crashing_cli(prompt, *, timeout_s=1200, forbid_edits=False, cwd=None):
        if forbid_edits:
            return {"ok": True, "output": "PLAN", "error": None}
        attempts["n"] += 1
        return {"ok": False, "output": "", "error": "boom"}

    monkeypatch.setattr(runners, "run_coding_cli", crashing_cli)
    final = _invoke(state)

    assert final["status"] == "failed"
    assert final["failure_reason"] == "implement_crash"
    assert attempts["n"] == 3  # 1 initial + 2 retries
    assert final["attempt"] == 3


def test_secret_in_staged_diff_blocks_commit(stubs, monkeypatch):
    """v2 §7.3: secret in staged diff -> secret_detected, nothing committed."""
    state = _base_state(stubs.repo, task_id="cli-secret")

    def leaky_cli(prompt, *, timeout_s=1200, forbid_edits=False, cwd=None):
        if forbid_edits:
            return {"ok": True, "output": "PLAN", "error": None}
        with open(f"{cwd}/calc.py", "a") as f:
            f.write('KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        return {"ok": True, "output": "done", "error": None}

    monkeypatch.setattr(runners, "run_coding_cli", leaky_cli)
    final = _invoke(state)

    assert final["status"] == "failed"
    assert final["failure_reason"] == "secret_detected"
    log = _real_git(stubs.repo, "log", "--format=%s", "-5")["stdout"]
    assert "orch: implement" not in log  # nothing committed


def test_pr_duplicate_guard_reuses_existing(stubs, monkeypatch):
    """수정2: existing PR for the head branch is reused, not re-created."""
    state = _base_state(stubs.repo, task_id="cli-dup")
    monkeypatch.setattr(runners, "run_tests",
                        lambda repo: {"passed": True, "output": "ok", "command": "pytest"})

    gh_calls = []

    def fake_gh(*args, repo_path=None):
        gh_calls.append(args)
        joined = " ".join(args)
        if joined.startswith("pr list"):
            return {"ok": True, "stdout": "https://example.test/pr/EXISTS", "stderr": "", "error": None}
        if joined.startswith("pr create"):
            raise AssertionError("pr create must not be called when PR already exists")
        return {"ok": True, "stdout": "", "stderr": "", "error": None}

    monkeypatch.setattr(runners, "gh", fake_gh)
    final = _invoke(state)

    assert final["status"] == "done"
    assert final["pr_url"] == "https://example.test/pr/EXISTS"
    assert not any(" ".join(a).startswith("pr create") for a in gh_calls)


def test_resume_skips_implement_when_marker_in_head(stubs, monkeypatch):
    """v2 §7.5: after a crash following the implement commit, re-running the
    task must NOT re-invoke the coding CLI — the marker in HEAD short-circuits
    straight to test (no duplicate commits)."""
    state = _base_state(stubs.repo, task_id="cli-mid")
    marker = make_marker("cli-mid", 0)

    # simulate the crashed run: branch exists with the implement commit already in
    subprocess.run(["git", "checkout", "-qb", "orch/cli-resume-test"], cwd=stubs.repo, check=True)
    with open(f"{stubs.repo}/calc.py", "a") as f:
        f.write("# implemented before crash\n")
    subprocess.run(["git", "-C", stubs.repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", stubs.repo, "commit", "-qm", f"orch: implement\n\n{marker}"], check=True)
    subprocess.run(["git", "checkout", "-q", "main"], cwd=stubs.repo, check=True)
    state["branch"] = "orch/cli-resume-test"

    edit_calls = {"n": 0}

    def counting_cli(prompt, *, timeout_s=1200, forbid_edits=False, cwd=None, **kw):
        if not forbid_edits:
            edit_calls["n"] += 1
        if "independent code reviewer" in prompt:
            return {"ok": True, "output": "fine\nVERDICT: PASS", "error": None}
        return {"ok": True, "output": "PLAN" if forbid_edits else "done", "error": None}

    monkeypatch.setattr(runners, "run_coding_cli", counting_cli)
    final = _invoke(state)

    assert final["status"] == "done"
    assert edit_calls["n"] == 0, "implement must be skipped when its marker is already in HEAD"
    # exactly one implement commit — no duplicates
    count = _real_git(stubs.repo, "rev-list", "--count", "main..orch/cli-resume-test")["stdout"].strip()
    assert count == "1"


def test_no_test_command_fails(stubs, monkeypatch):
    """v2 §7.6: no detectable test command -> no_test_command, no guessing."""
    state = _base_state(stubs.repo, task_id="cli-notest")
    monkeypatch.setattr(runners, "run_tests",
                        lambda repo: {"passed": None, "output": "", "command": None})
    final = _invoke(state)

    assert final["status"] == "failed"
    assert final["failure_reason"] == "no_test_command"


def test_analyze_signal_ignores_agent_metadata_noise():
    """수정6 fix: .graft/.opencode/.claude/.codex scaffolding is noise."""
    before = ""
    after = "?? .graft/\n?? .opencode/cache/\n"
    assert analyze_signal(after) == analyze_signal(before) == set()


def test_analyze_signal_still_catches_tracked_edits():
    before = ""
    after = "?? .graft/\n M notes.txt\n"
    assert analyze_signal(after) != analyze_signal(before)


def test_analyze_signal_still_catches_new_source_files():
    before = "?? .graft/\n"
    after = "?? .graft/\n?? evil.py\n"
    assert analyze_signal(after) != analyze_signal(before)


def test_create_branch_forks_from_base_not_current_checkout(stubs):
    """Regression (PR #5): a leftover checkout on a previous task's branch must
    not stack old commits into the new branch. New branch forks from base."""
    repo = stubs.repo
    _real_git(repo, "checkout", "-qb", "main")
    _real_git(repo, "checkout", "-qb", "orch/stale-task")
    with open(f"{repo}/stale.txt", "w") as f:
        f.write("x")
    _real_git(repo, "add", "-A")
    _real_git(repo, "commit", "-qm", "stale")
    state = _base_state(repo, task_id="cli-new")
    state["default_branch"] = "main"
    res = g.create_branch(state)
    assert res["branch"].startswith("orch/cli-")
    tip = _real_git(repo, "rev-parse", res["branch"])["stdout"].strip()
    main_tip = _real_git(repo, "rev-parse", "main")["stdout"].strip()
    assert tip == main_tip  # forked from base, not from the stale checkout
    stale = _real_git(repo, "rev-parse", "orch/stale-task")["stdout"].strip()
    log = _real_git(repo, "log", "--format=%H", res["branch"])["stdout"]
    assert stale not in log  # previous task's commit not dragged in


def test_after_test_pass_goes_to_review(stubs):
    from orch.graph import after_test
    assert after_test(_s(test_result={"passed": True})) == "review"


def test_after_review_routes(stubs):
    from orch.graph import after_review
    assert after_review(_s(review_passed=True)) == "create_pr"
    assert after_review(_s(review_passed=False, fix_attempt=0)) == "fix"
    assert after_review(_s(review_passed=False, failure_reason="test_failed_exhausted")) == "fail_task"


def test_review_node_parses_verdict(stubs, monkeypatch):
    import orch.graph as g
    from orch import runners
    monkeypatch.setattr(runners, "run_coding_cli",
                        lambda *a, **k: {"ok": True, "output": "looks good\nVERDICT: PASS", "error": None})
    monkeypatch.setattr(g, "runners", runners)
    state = _base_state(stubs.repo, task_id="cli-rev")
    res = g.review(state)
    assert res["review_passed"] is True
    monkeypatch.setattr(runners, "run_coding_cli",
                        lambda *a, **k: {"ok": True, "output": "missing null check\nVERDICT: FAIL", "error": None})
    res = g.review(state)
    assert res["review_passed"] is False and "null check" in res["review_notes"]
    monkeypatch.setattr(runners, "run_coding_cli",
                        lambda *a, **k: {"ok": False, "output": "", "error": "boom"})
    res = g.review(state)
    assert res["review_passed"] is False
